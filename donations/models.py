from django.db import models
from django.contrib.auth.models import User


class DonationCategory(models.Model):
    name = models.CharField(
        max_length=200,
        unique=True
    )
    description = models.TextField(
        blank=True
    )

    class Meta:
        verbose_name = "Donation Category"
        verbose_name_plural = "Donation Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


# Alias for backward compatibility
Category = DonationCategory


class Donation(models.Model):
    STATUS_AVAILABLE = 'AVAILABLE'
    STATUS_REQUESTED = 'REQUESTED'
    STATUS_APPROVED = 'APPROVED'
    STATUS_COLLECTED = 'COLLECTED'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_CANCELLED = 'CANCELLED'
    STATUS_EXPIRED = 'EXPIRED'

    STATUS_CHOICES = [
        ('AVAILABLE', 'Available'),
        ('REQUESTED', 'Requested'),
        ('APPROVED', 'Approved'),
        ('COLLECTED', 'Collected'),
        ('COMPLETED', 'Completed'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'),
        ('EXPIRED', 'Expired'),
    ]

    DELIVERY_NGO_PICKUP = 'NGO_PICKUP'
    DELIVERY_DONOR_DELIVERY = 'DONOR_DELIVERY'

    DELIVERY_CHOICES = [
        ('NGO_PICKUP', 'NGO/organization will pick up'),
        ('DONOR_DELIVERY', 'Donor will deliver/drop off'),
    ]

    donor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='donations'
    )
    category = models.ForeignKey(
        DonationCategory,
        on_delete=models.SET_NULL,
        null=True,
        related_name='donations'
    )
    title = models.CharField(
        max_length=200
    )
    description = models.TextField(
        blank=True
    )
    quantity = models.CharField(
        max_length=100
    )
    delivery_option = models.CharField(
        max_length=25,
        choices=DELIVERY_CHOICES,
        default='NGO_PICKUP',
        help_text="Transfer method: Donor drop-off vs NGO pickup"
    )
    dropoff_location = models.CharField(
        max_length=255,
        blank=True,
        help_text="Designated drop-off point, e.g. NGO center or community partner hub"
    )
    pickup_address = models.TextField()
    pickup_date = models.DateField(
        null=True,
        blank=True
    )
    pickup_time = models.TimeField(
        null=True,
        blank=True
    )
    expiry_date = models.DateTimeField(
        null=True,
        blank=True
    )
    image = models.ImageField(
        upload_to='donations/',
        blank=True,
        null=True
    )
    status = models.CharField(
        max_length=25,
        choices=STATUS_CHOICES,
        default='AVAILABLE'
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = "Donation"
        verbose_name_plural = "Donations"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - ({self.get_status_display()})"

    @property
    def is_available(self):
        return self.status == self.STATUS_AVAILABLE

    @property
    def city(self):
        profile = getattr(self.donor, 'profile', None)
        return getattr(profile, 'city', '') or ''

    @property
    def is_donor_delivery(self):
        return self.delivery_option == self.DELIVERY_DONOR_DELIVERY

    @property
    def is_ngo_pickup(self):
        return self.delivery_option == self.DELIVERY_NGO_PICKUP

    @property
    def is_small_donation(self):
        """
        Detects if donation is a micro-donation (e.g. 1-2 books, single meal packet, small parcel)
        where local walking pickup or donor drop-off is prioritized over vehicle collection.
        """
        import re
        text = f"{self.title or ''} {self.quantity or ''}".lower().strip()
        micro_patterns = [
            r'\b1\s*meal\b', r'\b2\s*meals?\b', r'\b1\s*book\b', r'\b2\s*books?\b',
            r'\b1-2\s*books?\b', r'\b1-2\s*meals?\b', r'\b1\s*packet\b', r'\b2\s*packets?\b',
            r'\b1\s*plate\b', r'\b2\s*plates?\b', r'\b1\s*item\b', r'\b2\s*items?\b',
            r'\bsingle\s*(meal|book|item|packet)\b', r'\bmicro\b'
        ]
        for pattern in micro_patterns:
            if re.search(pattern, text):
                return True
        q = (self.quantity or "").lower().strip()
        if re.match(r'^(1|2)\s*$', q):
            return True
        return False

    def change_status(self, new_status, user=None, remarks=""):
        self.status = new_status
        self.save(update_fields=['status', 'updated_at'])
