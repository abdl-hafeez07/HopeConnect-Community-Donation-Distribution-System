from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from .models import DonationRequest, DeliveryAssignment
from .forms import DonationRequestForm, DeliveryUpdateForm
from donations.models import Donation
from accounts.models import VolunteerProfile
from accounts.decorators import verified_ngo_required, donor_required, volunteer_required
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
    4. DeliveryAssignment created
    5. Notifications sent to approved NGO and local volunteers.
    """
    req_obj = get_object_or_404(DonationRequest, pk=request_id, donation__donor=request.user)

    if request.method == 'POST':
        notes = request.POST.get('donor_notes', '')
        delivery = req_obj.approve(donor=request.user, notes=notes)

        # Notify approved NGO
        send_notification(
            req_obj.ngo,
            f"Request Approved for '{req_obj.donation.title}'!",
            f"The donor approved your request. A delivery volunteer will be assigned shortly.",
            "REQUEST_APPROVED",
            link=f"/donations/{req_obj.donation.id}/"
        )

        # Notify active volunteers
        active_volunteers = VolunteerProfile.objects.filter(is_approved=True).select_related('user')
        for vol in active_volunteers:
            send_notification(
                vol.user,
                f"New Pickup Needed: {req_obj.donation.title}",
                f"A donation in {req_obj.donation.city} was approved and is ready for volunteer pickup.",
                "PICKUP_SCHEDULED",
                link="/requests/volunteer/pickups/"
            )

        messages.success(request, f"You approved the request from {req_obj.ngo.username}. The donation is now queued for volunteer pickup.")
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
@volunteer_required
def available_pickups(request):
    """
    Lists approved donations in need of volunteer pickup.
    """
    unassigned_deliveries = DeliveryAssignment.objects.filter(
        volunteer__isnull=True
    ).select_related('donation', 'donation__donor', 'request__ngo', 'request__ngo__profile', 'request__ngo__ngo_profile').order_by('-created_at')

    context = {
        'deliveries': unassigned_deliveries,
    }
    return render(request, 'donation_requests/available_pickups.html', context)


@login_required
@volunteer_required
def claim_pickup(request, assignment_id):
    """
    Volunteer claims an unassigned delivery task.
    """
    assignment = get_object_or_404(DeliveryAssignment, pk=assignment_id)

    if assignment.volunteer is not None:
        messages.warning(request, "This pickup has already been claimed by another volunteer.")
        return redirect('available_pickups')

    assignment.volunteer = request.user
    assignment.status = DeliveryAssignment.STATUS_ASSIGNED
    assignment.save()

    # Update donation status
    assignment.donation.change_status(
        Donation.STATUS_PICKUP_SCHEDULED,
        user=request.user,
        remarks=f"Claimed by volunteer {request.user.username}"
    )

    # Notify donor and NGO
    send_notification(
        assignment.donation.donor,
        f"Volunteer Assigned: {request.user.username}",
        f"Volunteer {request.user.username} has accepted to pick up and deliver your donation.",
        "PICKUP_SCHEDULED"
    )
    send_notification(
        assignment.request.ngo,
        f"Volunteer Assigned for Delivery",
        f"Volunteer {request.user.username} is handling pickup and delivery of '{assignment.donation.title}'.",
        "PICKUP_SCHEDULED"
    )

    messages.success(request, f"You have claimed the pickup for '{assignment.donation.title}'. Thank you!")
    return redirect('volunteer_dashboard')


@login_required
@volunteer_required
def update_delivery(request, assignment_id):
    """
    Volunteer updates delivery progress:
    - Schedule pickup time -> PICKUP_SCHEDULED
    - Confirm picked up from donor -> PICKED_UP
    - Confirm delivered to NGO -> DELIVERED & COMPLETED (with proof photo & recipient signature/notes).
    """
    assignment = get_object_or_404(
        DeliveryAssignment.objects.select_related('donation', 'donation__donor', 'request', 'request__ngo'),
        pk=assignment_id,
        volunteer=request.user
    )

    if request.method == 'POST':
        form = DeliveryUpdateForm(request.POST, request.FILES, instance=assignment)
        if form.is_valid():
            deliv = form.save(commit=False)

            # Check status updates
            new_status = form.cleaned_data['status']
            if new_status == DeliveryAssignment.STATUS_PICKED_UP:
                deliv.picked_up_at = timezone.now()
                assignment.donation.change_status(
                    Donation.STATUS_PICKED_UP,
                    user=request.user,
                    remarks=f"Volunteer picked up items from donor. Notes: {deliv.delivery_notes}"
                )
                send_notification(
                    assignment.request.ngo,
                    "Donation Picked Up!",
                    f"Volunteer {request.user.username} has picked up '{assignment.donation.title}' and is in transit.",
                    "PICKED_UP"
                )
            elif new_status == DeliveryAssignment.STATUS_DELIVERED:
                deliv.delivered_at = timezone.now()
                deliv.status = DeliveryAssignment.STATUS_DELIVERED
                assignment.donation.change_status(
                    Donation.STATUS_DELIVERED,
                    user=request.user,
                    remarks=f"Delivered to NGO by {request.user.username}. Handed to: {deliv.recipient_confirmation_name or 'Staff'}. Notes: {deliv.delivery_notes}"
                )
                # Notify NGO to confirm receipt
                send_notification(
                    assignment.request.ngo,
                    "Donation Delivered! Please Confirm Receipt",
                    f"Volunteer {request.user.username} has delivered '{assignment.donation.title}'. Please confirm receipt in your portal.",
                    "DELIVERED",
                    link="/dashboard/ngo/"
                )
                # Notify donor
                send_notification(
                    assignment.donation.donor,
                    "Donation Delivered to NGO",
                    f"Your donation '{assignment.donation.title}' was delivered to the NGO by volunteer {request.user.username}.",
                    "DELIVERED"
                )
            elif new_status == DeliveryAssignment.STATUS_COMPLETED:
                deliv.delivered_at = deliv.delivered_at or timezone.now()
                deliv.status = DeliveryAssignment.STATUS_COMPLETED
                assignment.donation.change_status(
                    Donation.STATUS_COMPLETED,
                    user=request.user,
                    remarks=f"Completed distribution. Handed to: {deliv.recipient_confirmation_name or 'NGO'}."
                )
                send_notification(
                    assignment.donation.donor,
                    "Donation Completed!",
                    f"Your donation '{assignment.donation.title}' distribution has been fully completed! Thank you for your impact.",
                    "COMPLETED"
                )
                send_notification(
                    assignment.request.ngo,
                    "Donation Completed",
                    f"Donation '{assignment.donation.title}' distribution marked as completed.",
                    "COMPLETED"
                )

            deliv.save()
            messages.success(request, f"Delivery status updated to '{deliv.get_status_display()}'.")
            return redirect('volunteer_dashboard')
    else:
        form = DeliveryUpdateForm(instance=assignment)

    context = {
        'assignment': assignment,
        'form': form,
    }
    return render(request, 'donation_requests/delivery_update.html', context)


@login_required
def confirm_receipt(request, assignment_id):
    """
    Allows the recipient NGO to confirm receipt of delivered donation,
    finalizing the distribution as COMPLETED.
    """
    assignment = get_object_or_404(
        DeliveryAssignment.objects.select_related('donation', 'donation__donor', 'volunteer', 'request'),
        pk=assignment_id,
        request__ngo=request.user
    )

    if request.method == 'POST':
        notes = request.POST.get('receipt_notes', 'Items received in good condition.')
        assignment.status = DeliveryAssignment.STATUS_COMPLETED
        if not assignment.delivered_at:
            assignment.delivered_at = timezone.now()
        assignment.delivery_notes += f"\n[NGO Confirmation]: {notes}"
        assignment.save()

        # Update donation to COMPLETED
        assignment.donation.change_status(
            Donation.STATUS_COMPLETED,
            user=request.user,
            remarks=f"Receipt confirmed by NGO: {request.user.username}. Notes: {notes}"
        )

        # Notify donor and volunteer
        send_notification(
            assignment.donation.donor,
            "Receipt Confirmed by NGO!",
            f"{request.user.username} confirmed receipt of '{assignment.donation.title}'. Distribution is now Completed!",
            "COMPLETED"
        )
        if assignment.volunteer:
            send_notification(
                assignment.volunteer,
                "Delivery Receipt Confirmed",
                f"{request.user.username} confirmed receipt of the donation you delivered. Thank you!",
                "COMPLETED"
            )

        messages.success(request, f"You have confirmed receipt of '{assignment.donation.title}'. Distribution is now marked as Completed!")

    return redirect('ngo_dashboard')

