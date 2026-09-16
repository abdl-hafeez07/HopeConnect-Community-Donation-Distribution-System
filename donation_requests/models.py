from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class DonationRequest(models.Model):
    """
    Represents an application by an NGO to receive an offered donation.
    Direct Donor -> NGO workflow without volunteer or third-party delivery tracking.
    """
    STATUS_PENDING = 'PENDING'
    STATUS_APPROVED = 'APPROVED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_COLLECTED = 'COLLECTED'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_CANCELLED = 'CANCELLED'

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('COLLECTED', 'Collected'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    donation = models.ForeignKey(
        'donations.Donation',
        on_delete=models.CASCADE,
        related_name='requests'
    )
    ngo = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ngo_requests'
    )
    message = models.TextField(
        blank=True
    )
    status = models.CharField(
        max_length=25,
        choices=STATUS_CHOICES,
        default='PENDING'
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = "Donation Request"
        verbose_name_plural = "Donation Requests"
        ordering = ['-created_at']

    def __str__(self):
        return f"Request by {self.ngo.username} for {self.donation.title} ({self.get_status_display()})"

    @property
    def requested_at(self):
        return self.created_at

    @property
    def responded_at(self):
        return self.updated_at

    @property
    def beneficiaries_count(self):
        return None

    @property
    def donor_notes(self):
        return ""

    def approve(self, donor=None, notes=""):
        """
        Approves this request, updates the donation status to APPROVED,
        and marks competing pending requests as REJECTED.
        """
        self.status = self.STATUS_APPROVED
        self.save(update_fields=['status', 'updated_at'])

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
        other_requests.update(status=self.STATUS_REJECTED)
        return self

    def reject(self, donor=None, notes=""):
        """
        Rejects this request. If no more pending requests exist, returns donation to AVAILABLE.
        """
        self.status = self.STATUS_REJECTED
        self.save(update_fields=['status', 'updated_at'])

        remaining_requests = self.donation.requests.filter(status=self.STATUS_PENDING).count()
        if remaining_requests == 0 and self.donation.status == 'REQUESTED':
            self.donation.change_status(
                'AVAILABLE',
                user=donor,
                remarks="All pending requests were rejected or cancelled."
            )
        return self
