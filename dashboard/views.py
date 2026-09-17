from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone

from accounts.models import UserProfile, NGOProfile
from accounts.decorators import admin_required
from donations.models import Donation
from donation_requests.models import DonationRequest
from core.utils import send_notification


@login_required
def dashboard_home(request):
    """
    Central router that dispatches users to their dedicated role dashboard.
    """
    if request.user.is_staff or request.user.is_superuser:
        return redirect('dashboard:admin_dashboard')

    profile = getattr(request.user, 'profile', None)
    if not profile:
        profile = UserProfile.objects.create(user=request.user, role='DONOR')

    if profile.role.upper() == 'NGO':
        return redirect('dashboard:ngo_dashboard')
    else:
        return redirect('dashboard:donor_dashboard')


@login_required
def donor_dashboard(request):
    """
    Dashboard for Donors:
    - Enforce login and check request.user.profile.role == 'DONOR'.
    - Metric counters: total_donations, available_count, pending_requests_count,
      approved_count, completed_count.
    - Query lists: active_requests, recent_donations.
    """
    profile = getattr(request.user, 'profile', None)
    user_role = getattr(profile, 'role', '').upper() if profile else ''

    if not request.user.is_staff and user_role != 'DONOR':
        messages.error(request, "Access restricted to Donors.")
        return redirect('dashboard:dashboard_home')

    my_donations = Donation.objects.filter(donor=request.user)

    total_donations = my_donations.count()
    available_count = my_donations.filter(status='AVAILABLE').count()
    approved_count = my_donations.filter(status='APPROVED').count()
    completed_count = my_donations.filter(status='COMPLETED').count()

    # Incoming requests on donor's donations that require approval/decision
    pending_requests_query = DonationRequest.objects.filter(
        donation__donor=request.user,
        status='PENDING'
    )
    pending_requests_count = pending_requests_query.count()

    active_requests = pending_requests_query.select_related(
        'donation', 'ngo', 'ngo__profile', 'ngo__ngo_profile'
    ).order_by('-created_at')

    recent_donations = my_donations.select_related('category').order_by('-created_at')[:5]

    # Confirmed handovers with assigned NGOs (Approved/Collected)
    approved_requests = DonationRequest.objects.filter(
        donation__donor=request.user,
        status__in=['APPROVED', 'COLLECTED']
    ).select_related(
        'donation', 'donation__category', 'ngo', 'ngo__profile', 'ngo__ngo_profile'
    ).order_by('-updated_at')

    context = {
        'total_donations': total_donations,
        'available_count': available_count,
        'pending_requests_count': pending_requests_count,
        'approved_count': approved_count,
        'completed_count': completed_count,
        'active_requests': active_requests,
        'approved_requests': approved_requests,
        'recent_donations': recent_donations,
        # Backward-compatibility aliases for templates
        'pending_requests': active_requests,
    }
    return render(request, 'dashboard/donor_dashboard.html', context)


@login_required
def ngo_dashboard(request):
    """
    Dashboard for NGOs:
    - Enforce login and check request.user.profile.role == 'NGO'.
    - Metric counters: available_donations_count, my_requests_count,
      pending_requests_count, approved_donations_count, completed_count.
    - Query lists: pickup_queue, recent_requests.
    - is_verified: boolean flag from request.user.profile.is_verified.
    """
    profile = getattr(request.user, 'profile', None)
    user_role = getattr(profile, 'role', '').upper() if profile else ''

    if not request.user.is_staff and user_role != 'NGO':
        messages.error(request, "Access restricted to NGOs.")
        return redirect('dashboard:dashboard_home')

    ngo_profile = getattr(request.user, 'ngo_profile', None)
    is_verified = bool(
        getattr(profile, 'is_verified', False) or
        (ngo_profile and ngo_profile.is_approved)
    )

    available_donations_count = Donation.objects.filter(status='AVAILABLE').count()

    my_requests = DonationRequest.objects.filter(ngo=request.user)
    my_requests_count = my_requests.count()
    pending_requests_count = my_requests.filter(status='PENDING').count()
    approved_donations_count = my_requests.filter(status='APPROVED').count()
    completed_count = my_requests.filter(status='COMPLETED').count()

    # Requests approved by donors awaiting collection by this NGO
    pickup_queue = my_requests.filter(status='APPROVED').select_related(
        'donation', 'donation__donor', 'donation__donor__profile', 'donation__category'
    ).order_by('-updated_at')

    # Latest 5 requests made by this NGO with current statuses
    recent_requests = my_requests.select_related(
        'donation', 'donation__donor', 'donation__category'
    ).order_by('-created_at')[:5]

    context = {
        'available_donations_count': available_donations_count,
        'my_requests_count': my_requests_count,
        'pending_requests_count': pending_requests_count,
        'approved_donations_count': approved_donations_count,
        'completed_count': completed_count,
        'pickup_queue': pickup_queue,
        'recent_requests': recent_requests,
        'is_verified': is_verified,
        'ngo_profile': ngo_profile,
        # Backward-compatibility aliases
        'approved_requests': pickup_queue,
        'my_requests': recent_requests,
    }
    return render(request, 'dashboard/ngo_dashboard.html', context)


@login_required
@admin_required
def admin_dashboard(request):
    """
    Admin control panel: verify NGOs, system-wide counts and monitoring.
    """
    pending_ngos = NGOProfile.objects.filter(is_approved=False).select_related('user', 'user__profile')

    total_users = User.objects.count()
    donor_count = UserProfile.objects.filter(role__iexact='DONOR').count()
    ngo_count = NGOProfile.objects.count()

    total_donations = Donation.objects.count()
    completed_donations = Donation.objects.filter(status='COMPLETED').count()

    recent_donations = Donation.objects.select_related('donor', 'category').order_by('-created_at')[:10]

    context = {
        'pending_ngos': pending_ngos,
        'total_users': total_users,
        'donor_count': donor_count,
        'ngo_count': ngo_count,
        'total_donations': total_donations,
        'completed_donations': completed_donations,
        'recent_donations': recent_donations,
    }
    return render(request, 'dashboard/admin_dashboard.html', context)


@login_required
@admin_required
def verify_ngo_action(request, pk, action):
    ngo = get_object_or_404(NGOProfile, pk=pk)
    if action == 'approve':
        ngo.is_approved = True
        ngo.verified_at = timezone.now()
        ngo.verified_by = request.user
        ngo.save()
        if hasattr(ngo.user, 'profile'):
            ngo.user.profile.is_verified = True
            ngo.user.profile.save()
        send_notification(
            ngo.user,
            "NGO Account Approved!",
            "Your NGO account has been verified by the HopeConnect team. You can now request donations.",
            "ACCOUNT_VERIFIED"
        )
        messages.success(request, f"NGO '{ngo.organization_name}' has been approved.")
    elif action == 'reject':
        ngo.is_approved = False
        ngo.save()
        messages.info(request, f"NGO '{ngo.organization_name}' approval rejected.")
    return redirect('dashboard:admin_dashboard')
