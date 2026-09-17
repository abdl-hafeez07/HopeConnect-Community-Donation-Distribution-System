from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction

from .models import DonationRequest
from .forms import DonationRequestForm
from donations.models import Donation
from accounts.decorators import donor_required, ngo_required
from core.utils import send_notification


@login_required
def submit_request(request, donation_id):
    """
    Allows a verified NGO to request an available donation.
    - Restrict to verified NGOs (role == 'NGO' and is_verified == True).
    - Prevent duplicate active requests by the same NGO on the same donation.
    - Set DonationRequest.status = 'PENDING' and update Donation.status = 'REQUESTED'.
    """
    profile = getattr(request.user, 'profile', None)
    user_role = getattr(profile, 'role', '').upper() if profile else ''

    if user_role != 'NGO':
        messages.error(request, "Only registered NGOs can submit donation requests.")
        return redirect('donation_detail', pk=donation_id)

    ngo_profile = getattr(request.user, 'ngo_profile', None)
    is_verified = bool(getattr(profile, 'is_verified', False) or (ngo_profile and ngo_profile.is_approved))
    if not is_verified:
        messages.warning(request, "Admin verification required to request items.")
        return redirect('donation_detail', pk=donation_id)

    donation = get_object_or_404(Donation, pk=donation_id)

    if donation.status not in ['AVAILABLE', 'REQUESTED']:
        messages.error(request, "This donation is no longer available for requests.")
        return redirect('donation_detail', pk=donation.id)

    # Prevent duplicate active requests by the same NGO
    existing_request = DonationRequest.objects.filter(
        donation=donation,
        ngo=request.user,
        status__in=['PENDING', 'APPROVED', 'COLLECTED']
    ).first()
    if existing_request:
        messages.info(request, "Your organization already has an active request for this donation.")
        return redirect('donation_detail', pk=donation.id)

    if request.method == 'POST':
        form = DonationRequestForm(request.POST, user=request.user)
        if form.is_valid():
            with transaction.atomic():
                req_obj = form.save(commit=False)
                req_obj.donation = donation
                req_obj.ngo = request.user
                req_obj.status = 'PENDING'

                # If contact fields were omitted in submission, populate with registered NGO profile details
                if not req_obj.contact_person:
                    req_obj.contact_person = (ngo_profile and ngo_profile.contact_person) or request.user.get_full_name() or request.user.username
                if not req_obj.contact_phone and profile and profile.phone:
                    req_obj.contact_phone = profile.phone
                if not req_obj.contact_email:
                    req_obj.contact_email = request.user.email or ''
                if not req_obj.pickup_notes and profile and profile.address:
                    req_obj.pickup_notes = f"Organization Address: {profile.address}"

                req_obj.save()

                donation.status = 'REQUESTED'
                donation.save(update_fields=['status', 'updated_at'])

            # Notify donor
            ngo_name = getattr(ngo_profile, 'organization_name', request.user.username)
            send_notification(
                donation.donor,
                f"New Request from {ngo_name}",
                f"{ngo_name} requested your donation '{donation.title}'.",
                "REQUEST_RECEIVED",
                link=f"/requests/review/{donation.id}/"
            )

            messages.success(request, f"Your request for '{donation.title}' has been submitted to the donor.")
            return redirect('donation_detail', pk=donation.id)
    else:
        form = DonationRequestForm(user=request.user)

    context = {
        'donation': donation,
        'form': form,
        'ngo_profile': ngo_profile,
        'profile': profile,
    }
    return render(request, 'donation_requests/request_form.html', context)


# Aliases for backward compatibility and semantic workflow naming
request_donation = submit_request


def accept_request(request, donation_id=None, request_id=None):
    """
    Accept-request handler supporting both:
    - NGO accepting a donor's donation listing (donation_id)
    - Donor approving an NGO's request (request_id)
    """
    if donation_id is not None:
        return submit_request(request, donation_id=donation_id)
    if request_id is not None:
        return manage_request(request, request_id=request_id, action='approve')
    return redirect('dashboard:dashboard_home')


@login_required
def donor_review_requests(request, donation_id):
    """
    Donor reviews all incoming NGO applications for a specific donation.
    """
    donation = get_object_or_404(Donation, pk=donation_id, donor=request.user)
    requests = donation.requests.select_related('ngo', 'ngo__profile', 'ngo__ngo_profile').order_by('-created_at')

    context = {
        'donation': donation,
        'requests': requests,
    }
    return render(request, 'donation_requests/donor_requests_list.html', context)


@login_required
def manage_request(request, request_id, action):
    """
    Manage an NGO request on a donation.
    - Restricted to the Donor who owns the item.
    - If action == 'approve':
        * Set DonationRequest.status = 'APPROVED'.
        * Set Donation.status = 'APPROVED'.
        * Automatically reject any other pending requests for the same item.
    - If action == 'reject':
        * Set DonationRequest.status = 'REJECTED'.
        * If no other pending requests exist, revert Donation.status = 'AVAILABLE'.
    """
    req_obj = get_object_or_404(
        DonationRequest.objects.select_related('donation', 'ngo'),
        pk=request_id
    )

    if req_obj.donation.donor != request.user:
        messages.error(request, "Access restricted. You do not own this donation.")
        return redirect('dashboard:donor_dashboard')

    action = action.lower()

    if action == 'approve':
        with transaction.atomic():
            req_obj.status = 'APPROVED'
            req_obj.save(update_fields=['status', 'updated_at'])

            req_obj.donation.status = 'APPROVED'
            req_obj.donation.save(update_fields=['status', 'updated_at'])

            # Automatically reject competing pending requests on the same item
            req_obj.donation.requests.filter(
                status='PENDING'
            ).exclude(id=req_obj.id).update(status='REJECTED')

        send_notification(
            req_obj.ngo,
            f"Request Approved for '{req_obj.donation.title}'!",
            "The donor approved your request. Coordinate pickup directly with the donor.",
            "REQUEST_APPROVED",
            link=f"/donations/{req_obj.donation.id}/"
        )
        messages.success(request, f"You approved the request from {req_obj.ngo.username}.")

    elif action == 'reject':
        with transaction.atomic():
            req_obj.status = 'REJECTED'
            req_obj.save(update_fields=['status', 'updated_at'])

            # If no other pending requests exist, revert Donation to AVAILABLE
            pending_count = req_obj.donation.requests.filter(status='PENDING').count()
            if pending_count == 0 and req_obj.donation.status == 'REQUESTED':
                req_obj.donation.status = 'AVAILABLE'
                req_obj.donation.save(update_fields=['status', 'updated_at'])

        send_notification(
            req_obj.ngo,
            f"Request Declined for '{req_obj.donation.title}'",
            "The donor was unable to accept your request at this time.",
            "REQUEST_REJECTED",
            link=f"/donations/{req_obj.donation.id}/"
        )
        messages.info(request, f"Request from {req_obj.ngo.username} was rejected.")

    else:
        messages.error(request, f"Unknown action '{action}'.")

    return redirect('review_requests', donation_id=req_obj.donation.id)


def approve_request(request, request_id):
    """Alias delegating to manage_request with action='approve'."""
    return manage_request(request, request_id, action='approve')


def reject_request(request, request_id):
    """Alias delegating to manage_request with action='reject'."""
    return manage_request(request, request_id, action='reject')


@login_required
def mark_collected(request, request_id):
    """
    Restrict to the assigned NGO.
    Updates DonationRequest.status = 'COLLECTED' and Donation.status = 'COLLECTED'.
    """
    req_obj = get_object_or_404(
        DonationRequest.objects.select_related('donation', 'ngo'),
        pk=request_id
    )

    if req_obj.ngo != request.user:
        messages.error(request, "Access restricted. Only the assigned NGO can mark this as collected.")
        return redirect('dashboard:ngo_dashboard')

    if req_obj.status != 'APPROVED':
        messages.error(request, "Only approved requests can be marked as collected.")
        return redirect('donation_detail', pk=req_obj.donation.id)

    with transaction.atomic():
        req_obj.status = 'COLLECTED'
        req_obj.save(update_fields=['status', 'updated_at'])

        req_obj.donation.status = 'COLLECTED'
        req_obj.donation.save(update_fields=['status', 'updated_at'])

    send_notification(
        req_obj.donation.donor,
        f"Donation Collected: {req_obj.donation.title}",
        f"{req_obj.ngo.username} has marked your donation as collected.",
        "STATUS_UPDATE",
        link=f"/donations/{req_obj.donation.id}/"
    )

    messages.success(request, f"Donation '{req_obj.donation.title}' marked as collected.")
    return redirect('dashboard:ngo_dashboard')


@login_required
def mark_completed(request, request_id):
    """
    Triggered by either the NGO confirming final receipt or Donor confirming handoff.
    Updates DonationRequest.status = 'COMPLETED' and Donation.status = 'COMPLETED'.
    """
    req_obj = get_object_or_404(
        DonationRequest.objects.select_related('donation', 'donation__donor', 'ngo'),
        pk=request_id
    )

    is_donor = (req_obj.donation.donor == request.user)
    is_assigned_ngo = (req_obj.ngo == request.user)

    if not (is_donor or is_assigned_ngo):
        messages.error(request, "Access restricted. Only the donor or assigned NGO can mark this as completed.")
        return redirect('dashboard:dashboard_home')

    if req_obj.status not in ['APPROVED', 'COLLECTED']:
        messages.error(request, "This donation cannot be completed in its current state.")
        return redirect('donation_detail', pk=req_obj.donation.id)

    with transaction.atomic():
        req_obj.status = 'COMPLETED'
        req_obj.save(update_fields=['status', 'updated_at'])

        req_obj.donation.status = 'COMPLETED'
        req_obj.donation.save(update_fields=['status', 'updated_at'])

    # Notify counterparty
    counterparty = req_obj.donation.donor if is_assigned_ngo else req_obj.ngo
    send_notification(
        counterparty,
        f"Donation Completed: {req_obj.donation.title}",
        f"The donation '{req_obj.donation.title}' has been successfully completed!",
        "COMPLETED",
        link=f"/donations/{req_obj.donation.id}/"
    )

    messages.success(request, f"Donation '{req_obj.donation.title}' is now marked as completed!")

    if is_donor:
        return redirect('my_donations')
    return redirect('dashboard:ngo_dashboard')


# Alias for backward compatibility
confirm_receipt = mark_completed
