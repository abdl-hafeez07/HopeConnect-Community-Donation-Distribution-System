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

    def change_status(self, new_status, user=None, remarks=""):
        self.status = new_status
        self.save(update_fields=['status', 'updated_at'])
