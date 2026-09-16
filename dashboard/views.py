from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone

from accounts.models import UserProfile, NGOProfile
from accounts.decorators import donor_required, ngo_required, admin_required
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
@donor_required
def donor_dashboard(request):
    """
    Dashboard for Donors: view stats, incoming NGO requests, and recent donations.
    """
    user = request.user
    my_donations = Donation.objects.filter(donor=user).select_related('category')

    total_donations = my_donations.count()
    active_donations = my_donations.filter(status__in=['AVAILABLE', 'REQUESTED', 'APPROVED', 'COLLECTED']).count()
    completed_donations = my_donations.filter(status='COMPLETED').count()

    # Incoming requests on donor's donations that require approval/decision
    pending_requests = DonationRequest.objects.filter(
        donation__donor=user,
        status='PENDING'
    ).select_related('donation', 'ngo', 'ngo__profile').order_by('-created_at')

    recent_donations = my_donations.order_by('-created_at')[:5]

    context = {
        'total_donations': total_donations,
        'active_donations': active_donations,
        'completed_donations': completed_donations,
        'pending_requests': pending_requests,
        'recent_donations': recent_donations,
    }
    return render(request, 'dashboard/donor_dashboard.html', context)


@login_required
@ngo_required
def ngo_dashboard(request):
    """
    Dashboard for NGOs: review verification status, active requests, and approved donations awaiting pickup/completion.
    """
    user = request.user
    ngo_profile = getattr(user, 'ngo_profile', None)

    my_requests = DonationRequest.objects.filter(ngo=user).select_related('donation', 'donation__donor').order_by('-created_at')
    total_requested = my_requests.count()
    pending_count = my_requests.filter(status='PENDING').count()
    approved_count = my_requests.filter(status='APPROVED').count()

    # Approved donations awarded to this NGO that can be confirmed/completed
    approved_requests = DonationRequest.objects.filter(
        ngo=user,
        status='APPROVED'
    ).select_related('donation', 'donation__donor', 'donation__category').order_by('-updated_at')

    # Available community donations
    available_donations = Donation.objects.filter(
        status='AVAILABLE'
    ).select_related('category', 'donor').order_by('-created_at')[:6]

    context = {
        'ngo_profile': ngo_profile,
        'total_requested': total_requested,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'my_requests': my_requests[:5],
        'approved_requests': approved_requests,
        'available_donations': available_donations,
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
