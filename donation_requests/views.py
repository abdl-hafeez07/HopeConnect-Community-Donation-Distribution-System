from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from .models import DonationRequest
from .forms import DonationRequestForm
from donations.models import Donation
from accounts.decorators import verified_ngo_required, donor_required, ngo_required
from core.utils import send_notification


@login_required
@verified_ngo_required
def request_donation(request, donation_id):
    """
    Allows a verified NGO to request an available donation.
    """
    donation = get_object_or_404(Donation, pk=donation_id)

    if donation.status != Donation.STATUS_AVAILABLE:
        messages.error(request, "This donation is no longer available for requests.")
        return redirect('donation_detail', pk=donation.id)

    existing_request = DonationRequest.objects.filter(donation=donation, ngo=request.user).first()
    if existing_request:
        messages.info(request, "Your organization has already submitted a request for this donation.")
        return redirect('donation_detail', pk=donation.id)

    if request.method == 'POST':
        form = DonationRequestForm(request.POST)
        if form.is_valid():
            req_obj = form.save(commit=False)
            req_obj.donation = donation
            req_obj.ngo = request.user
            req_obj.status = DonationRequest.STATUS_PENDING
            req_obj.save()

            # Mark donation as REQUESTED
            donation.change_status(
                Donation.STATUS_REQUESTED,
                user=request.user,
                remarks=f"Request submitted by NGO: {request.user.username}"
            )

            # Notify donor
            ngo_name = request.user.ngo_profile.organization_name if hasattr(request.user, 'ngo_profile') else request.user.username
            send_notification(
                donation.donor,
                f"New Request from {ngo_name}",
                f"{ngo_name} requested your donation '{donation.title}' for {req_obj.beneficiaries_count} beneficiaries.",
                "REQUEST_RECEIVED",
                link=f"/requests/review/{donation.id}/"
            )

            messages.success(request, f"Your request for '{donation.title}' has been sent to the donor for review.")
            return redirect('donation_detail', pk=donation.id)
    else:
        form = DonationRequestForm()

    context = {
        'donation': donation,
        'form': form,
    }
    return render(request, 'donation_requests/request_form.html', context)


@login_required
@donor_required
def donor_review_requests(request, donation_id):
    """
    Donor reviews all incoming NGO applications for a specific donation.
    """
    donation = get_object_or_404(Donation, pk=donation_id, donor=request.user)
    requests = donation.requests.select_related('ngo', 'ngo__profile', 'ngo__ngo_profile').order_by('-requested_at')

    context = {
        'donation': donation,
        'requests': requests,
    }
    return render(request, 'donation_requests/donor_requests_list.html', context)


@login_required
@donor_required
def approve_request(request, request_id):
    """
    Donor approves an NGO's request.
    This triggers:
    1. Request marked as APPROVED
    2. Other pending requests rejected
    3. Donation status changed to APPROVED
    4. Notification sent to approved NGO.
    """
    req_obj = get_object_or_404(DonationRequest, pk=request_id, donation__donor=request.user)

    if request.method == 'POST':
        notes = request.POST.get('donor_notes', '')
        req_obj.approve(donor=request.user, notes=notes)

        # Notify approved NGO
        send_notification(
            req_obj.ngo,
            f"Request Approved for '{req_obj.donation.title}'!",
            f"The donor approved your request. You can now coordinate pickup directly with the donor.",
            "REQUEST_APPROVED",
            link=f"/donations/{req_obj.donation.id}/"
        )

        messages.success(request, f"You approved the request from {req_obj.ngo.username}. The donation is now awarded to this NGO.")
        return redirect('review_requests', donation_id=req_obj.donation.id)

    return redirect('review_requests', donation_id=req_obj.donation.id)


@login_required
@donor_required
def reject_request(request, request_id):
    """
    Donor rejects an individual request.
    """
    req_obj = get_object_or_404(DonationRequest, pk=request_id, donation__donor=request.user)

    if request.method == 'POST':
        notes = request.POST.get('donor_notes', 'Request was declined by donor.')
        req_obj.reject(donor=request.user, notes=notes)

        send_notification(
            req_obj.ngo,
            f"Request Declined for '{req_obj.donation.title}'",
            f"The donor was unable to accept your request at this time. Notes: {notes}",
            "REQUEST_REJECTED",
            link=f"/donations/{req_obj.donation.id}/"
        )

        messages.info(request, f"Request from {req_obj.ngo.username} was rejected.")

    return redirect('review_requests', donation_id=req_obj.donation.id)


@login_required
@ngo_required
def confirm_receipt(request, request_id):
    """
    Allows the recipient NGO to confirm receipt of the approved donation,
    finalizing the distribution as COMPLETED.
    """
    req_obj = get_object_or_404(
        DonationRequest.objects.select_related('donation', 'donation__donor', 'ngo'),
        pk=request_id,
        ngo=request.user,
        status=DonationRequest.STATUS_APPROVED
    )

    if request.method == 'POST':
        notes = request.POST.get('receipt_notes', 'Items received in good condition.')

        # Update donation to COMPLETED
        req_obj.donation.change_status(
            Donation.STATUS_COMPLETED,
            user=request.user,
            remarks=f"Receipt confirmed by NGO: {request.user.username}. Notes: {notes}"
        )

        # Notify donor
        send_notification(
            req_obj.donation.donor,
            "Receipt Confirmed by NGO!",
            f"{request.user.username} confirmed receipt of '{req_obj.donation.title}'. Distribution is now Completed!",
            "COMPLETED",
            link=f"/donations/{req_obj.donation.id}/"
        )

        messages.success(request, f"You have confirmed receipt of '{req_obj.donation.title}'. Distribution is now marked as Completed!")

    return redirect('dashboard:ngo_dashboard')

