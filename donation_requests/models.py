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
    # Confirmed contact details shared with donor upon request acceptance
    contact_person = models.CharField(
        max_length=150,
        blank=True,
        help_text="Confirmed NGO contact person name"
    )
    contact_phone = models.CharField(
        max_length=30,
        blank=True,
        help_text="Confirmed NGO contact phone number"
    )
    contact_email = models.EmailField(
        blank=True,
        help_text="Confirmed NGO contact email"
    )
    pickup_notes = models.TextField(
        blank=True,
        help_text="Confirmed logistics, pickup preference, or address notes"
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

    @property
    def confirmed_organization(self):
        ngo_profile = getattr(self.ngo, 'ngo_profile', None)
        if ngo_profile and ngo_profile.organization_name:
            return ngo_profile.organization_name
        return self.ngo.username

    @property
    def confirmed_contact_person(self):
        if self.contact_person:
            return self.contact_person
        ngo_profile = getattr(self.ngo, 'ngo_profile', None)
        if ngo_profile and ngo_profile.contact_person:
            return ngo_profile.contact_person
        return self.ngo.get_full_name() or self.ngo.username

    @property
    def confirmed_phone(self):
        if self.contact_phone:
            return self.contact_phone
        profile = getattr(self.ngo, 'profile', None)
        return getattr(profile, 'phone', '') or ''

    @property
    def confirmed_email(self):
        if self.contact_email:
            return self.contact_email
        return self.ngo.email or ''

    @property
    def confirmed_address(self):
        if self.pickup_notes:
            return self.pickup_notes
        profile = getattr(self.ngo, 'profile', None)
        return getattr(profile, 'address', '') or ''

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
