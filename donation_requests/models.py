from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class DonationRequest(models.Model):
    """
    Represents an application by a verified NGO to receive a posted donation.
    """
    STATUS_PENDING = 'PENDING'
    STATUS_APPROVED = 'APPROVED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_CANCELLED = 'CANCELLED'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending Review'),
        (STATUS_APPROVED, 'Approved by Donor'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_CANCELLED, 'Cancelled by NGO'),
    ]

    donation = models.ForeignKey(
        'donations.Donation',
        on_delete=models.CASCADE,
        related_name='requests'
    )
    ngo = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='donation_requests'
    )
    message = models.TextField(
        help_text="Explain how your NGO plans to distribute this donation and who will benefit."
    )
    beneficiaries_count = models.PositiveIntegerField(
        default=1,
        help_text="Estimated number of beneficiaries"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )
    requested_at = models.DateTimeField(
        auto_now_add=True
    )
    responded_at = models.DateTimeField(
        null=True,
        blank=True
    )
    donor_notes = models.TextField(
        blank=True,
        help_text="Optional remarks from the donor when accepting or rejecting the request."
    )

    class Meta:
        verbose_name = "Donation Request"
        verbose_name_plural = "Donation Requests"
        ordering = ['-requested_at']

    def __str__(self):
        return f"Request by {self.ngo.username} for {self.donation.title} ({self.get_status_display()})"

    def approve(self, donor=None, notes=""):
        """
        Approves this request, updates the donation status,
        and rejects competing pending requests for this donation.
        """
        self.status = self.STATUS_APPROVED
        self.responded_at = timezone.now()
        self.donor_notes = notes
        self.save()

        # Update donation status
        self.donation.change_status(
            'APPROVED',
            user=donor,
            remarks=f"Approved for NGO: {self.ngo.username}"
        )

        # Automatically reject other pending requests on the same donation
        other_requests = self.donation.requests.filter(
            status=self.STATUS_PENDING
        ).exclude(id=self.id)
        other_requests.update(
            status=self.STATUS_REJECTED,
            responded_at=timezone.now(),
            donor_notes="Donation was awarded to another organization."
        )
        return self

    def reject(self, donor=None, notes=""):
        """
        Rejects this request. If no more pending requests exist, returns donation to AVAILABLE.
        """
        self.status = self.STATUS_REJECTED
        self.responded_at = timezone.now()
        self.donor_notes = notes
        self.save()

        remaining_requests = self.donation.requests.filter(status=self.STATUS_PENDING).count()
        if remaining_requests == 0 and self.donation.status == 'REQUESTED':
            self.donation.change_status(
                'AVAILABLE',
                user=donor,
                remarks="All pending requests were rejected or cancelled."
            )
