from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone

from accounts.models import UserProfile, NGOProfile, VolunteerProfile
from accounts.decorators import donor_required, ngo_required, volunteer_required, admin_required
from donations.models import Donation
from donation_requests.models import DonationRequest, DeliveryAssignment
from core.utils import send_notification


@login_required
def dashboard_home(request):
    """
    Central router that dispatches users to their dedicated role dashboard.
    """
    if request.user.is_staff or request.user.is_superuser:
        return redirect('/admin/')

    profile = getattr(request.user, 'profile', None)
    if not profile:
        profile = UserProfile.objects.create(user=request.user, role='Donor')

    if profile.role == 'NGO':
        return redirect('ngo_dashboard')
    elif profile.role == 'Volunteer':
        return redirect('volunteer_dashboard')
    else:
        return redirect('donor_dashboard')


@login_required
@donor_required
def donor_dashboard(request):
    """
    Dashboard for Donors: view stats, incoming NGO requests, and recent donations.
    """
    user = request.user
    my_donations = Donation.objects.filter(donor=user).select_related('category')

    total_donations = my_donations.count()
    active_donations = my_donations.filter(status__in=['AVAILABLE', 'REQUESTED', 'APPROVED', 'PICKUP_SCHEDULED', 'PICKED_UP']).count()
    completed_donations = my_donations.filter(status='COMPLETED').count()

    # Incoming requests on donor's donations that require approval/decision
    pending_requests = DonationRequest.objects.filter(
        donation__donor=user,
        status='PENDING'
    ).select_related('donation', 'ngo', 'ngo__profile').order_by('-requested_at')

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
    Dashboard for NGOs: review verification status, active requests, and incoming deliveries.
    """
    user = request.user
    ngo_profile = getattr(user, 'ngo_profile', None)

    my_requests = DonationRequest.objects.filter(ngo=user).select_related('donation', 'donation__donor').order_by('-requested_at')
    total_requested = my_requests.count()
    pending_count = my_requests.filter(status='PENDING').count()
    approved_count = my_requests.filter(status='APPROVED').count()

    # Active deliveries headed to this NGO (including those awaiting receipt confirmation)
    incoming_deliveries = DeliveryAssignment.objects.filter(
        request__ngo=user,
        status__in=['ASSIGNED', 'PICKUP_SCHEDULED', 'PICKED_UP', 'DELIVERED']
    ).select_related('donation', 'volunteer', 'request')

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
        'incoming_deliveries': incoming_deliveries,
        'available_donations': available_donations,
    }
    return render(request, 'dashboard/ngo_dashboard.html', context)


@login_required
@volunteer_required
def volunteer_dashboard(request):
    """
    Dashboard for Volunteers: available pickups to claim, assigned tasks, and completion history.
    """
    user = request.user
    vol_profile = getattr(user, 'volunteer_profile', None)

    # Deliveries assigned to this volunteer that are in progress
    active_deliveries = DeliveryAssignment.objects.filter(
        volunteer=user,
        status__in=['ASSIGNED', 'PICKUP_SCHEDULED', 'PICKED_UP']
    ).select_related('donation', 'request', 'request__ngo', 'donation__donor')

    # Unassigned deliveries waiting for a volunteer
    unassigned_deliveries = DeliveryAssignment.objects.filter(
        volunteer__isnull=True,
        status__in=['ASSIGNED', 'PICKUP_SCHEDULED']
    ).select_related('donation', 'request', 'request__ngo', 'donation__donor').order_by('-created_at')

    # Completed deliveries by this volunteer
    completed_deliveries = DeliveryAssignment.objects.filter(
        volunteer=user,
        status__in=['DELIVERED', 'COMPLETED']
    ).count()

    context = {
        'vol_profile': vol_profile,
        'active_deliveries': active_deliveries,
        'unassigned_deliveries': unassigned_deliveries,
        'completed_deliveries': completed_deliveries,
    }
    return render(request, 'dashboard/volunteer_dashboard.html', context)


@login_required
@admin_required
def admin_dashboard(request):
    """
    Admin control panel: verify NGOs & Volunteers, system-wide counts and monitoring.
    """
    pending_ngos = NGOProfile.objects.filter(is_approved=False).select_related('user', 'user__profile')
    pending_volunteers = VolunteerProfile.objects.filter(is_approved=False).select_related('user', 'user__profile')

    total_users = User.objects.count()
    donor_count = UserProfile.objects.filter(role='Donor').count()
    ngo_count = NGOProfile.objects.count()
    vol_count = VolunteerProfile.objects.count()

    total_donations = Donation.objects.count()
    completed_donations = Donation.objects.filter(status='COMPLETED').count()

    recent_donations = Donation.objects.select_related('donor', 'category').order_by('-created_at')[:10]

    context = {
        'pending_ngos': pending_ngos,
        'pending_volunteers': pending_volunteers,
        'total_users': total_users,
        'donor_count': donor_count,
        'ngo_count': ngo_count,
        'vol_count': vol_count,
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
    return redirect('admin_dashboard')


@login_required
@admin_required
def verify_volunteer_action(request, pk, action):
    vol = get_object_or_404(VolunteerProfile, pk=pk)
    if action == 'approve':
        vol.is_approved = True
        vol.verified_at = timezone.now()
        vol.verified_by = request.user
        vol.save()
        if hasattr(vol.user, 'profile'):
            vol.user.profile.is_verified = True
            vol.user.profile.save()
        send_notification(
            vol.user,
            "Volunteer Verification Approved!",
            "Your volunteer profile has been approved. You can now accept donation pickup & delivery tasks.",
            "ACCOUNT_VERIFIED"
        )
        messages.success(request, f"Volunteer '{vol.user.username}' has been approved.")
    elif action == 'reject':
        vol.is_approved = False
        vol.save()
        messages.info(request, f"Volunteer '{vol.user.username}' was rejected.")
    return redirect('admin_dashboard')
