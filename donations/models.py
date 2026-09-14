from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError


class Category(models.Model):
    """
    Categories for donations (e.g. Food, Clothing, Books, Medical, Toys).
    """
    name = models.CharField(
        max_length=100,
        unique=True
    )
    description = models.TextField(
        blank=True
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="Bootstrap icon class name, e.g. bi-egg-fried, bi-book"
    )
    is_active = models.BooleanField(
        default=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Donation Category"
        verbose_name_plural = "Donation Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class Donation(models.Model):
    """
    Represents an item or batch of items offered by a donor.
    Tracks state through the entire lifecycle:
    Available -> Requested -> Approved -> Pickup Scheduled -> Picked Up -> Delivered -> Completed
    """
    STATUS_AVAILABLE = 'AVAILABLE'
    STATUS_REQUESTED = 'REQUESTED'
    STATUS_APPROVED = 'APPROVED'
    STATUS_PICKUP_SCHEDULED = 'PICKUP_SCHEDULED'
    STATUS_PICKED_UP = 'PICKED_UP'
    STATUS_DELIVERED = 'DELIVERED'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_CANCELLED = 'CANCELLED'

    STATUS_CHOICES = [
        (STATUS_AVAILABLE, 'Available'),
        (STATUS_REQUESTED, 'Requested'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_PICKUP_SCHEDULED, 'Pickup Scheduled'),
        (STATUS_PICKED_UP, 'Picked Up'),
        (STATUS_DELIVERED, 'Delivered'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    donor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='donations'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='donations'
    )
    title = models.CharField(
        max_length=200
    )
    description = models.TextField()
    quantity = models.CharField(
        max_length=100,
        help_text="e.g., 50 cooked meal boxes, 2 bags of clothes, 10 books"
    )
    pickup_address = models.TextField()
    city = models.CharField(
        max_length=100
    )
    pickup_landmark = models.CharField(
        max_length=200,
        blank=True
    )
    preferred_pickup_time = models.DateTimeField(
        null=True,
        blank=True
    )
    image = models.ImageField(
        upload_to='donations/',
        blank=True,
        null=True
    )
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_AVAILABLE
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
    def is_food(self):
        return hasattr(self, 'food_detail') or self.category.name.lower() == 'food'

    @property
    def is_available(self):
        return self.status == self.STATUS_AVAILABLE

    def change_status(self, new_status, user=None, remarks=""):
        """
        Updates the donation status and records an entry in the audit history.
        """
        self.status = new_status
        self.save(update_fields=['status', 'updated_at'])
        DonationStatusHistory.objects.create(
            donation=self,
            status=new_status,
            changed_by=user,
            remarks=remarks
        )


class FoodDetail(models.Model):
    """
    Specific attributes required for food donations (safety, expiry, preservation).
    """
    FOOD_TYPES = [
        ('Cooked Meals', 'Cooked Meals'),
        ('Raw Groceries', 'Raw Groceries'),
        ('Packaged Food', 'Packaged Food'),
    ]

    DIETARY_CHOICES = [
        ('Vegetarian', 'Vegetarian'),
        ('Non-Vegetarian', 'Non-Vegetarian'),
        ('Vegan', 'Vegan'),
    ]

    donation = models.OneToOneField(
        Donation,
        on_delete=models.CASCADE,
        related_name='food_detail'
    )
    food_type = models.CharField(
        max_length=50,
        choices=FOOD_TYPES,
        default='Cooked Meals'
    )
    preparation_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the food was cooked or packed"
    )
    expiry_time = models.DateTimeField(
        help_text="Safe consumption deadline"
    )
    storage_instructions = models.CharField(
        max_length=255,
        blank=True,
        help_text="e.g., Keep refrigerated, Consume within 3 hours"
    )
    dietary_type = models.CharField(
        max_length=30,
        choices=DIETARY_CHOICES,
        default='Vegetarian'
    )

    class Meta:
        verbose_name = "Food Detail"
        verbose_name_plural = "Food Details"

    def clean(self):
        if self.expiry_time and self.expiry_time <= timezone.now():
            raise ValidationError({'expiry_time': 'Expiry time must be in the future.'})

    @property
    def is_expired(self):
        return timezone.now() > self.expiry_time

    def __str__(self):
        return f"Food Details for {self.donation.title} (Expires: {self.expiry_time.strftime('%Y-%m-%d %H:%M')})"


class DonationStatusHistory(models.Model):
    """
    Audit log of status updates across the donation lifecycle.
    """
    donation = models.ForeignKey(
        Donation,
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    status = models.CharField(
        max_length=30
    )
    changed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    remarks = models.TextField(
        blank=True
    )
    timestamp = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Donation Status History"
        verbose_name_plural = "Donation Status Histories"
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.donation.title} -> {self.status} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
