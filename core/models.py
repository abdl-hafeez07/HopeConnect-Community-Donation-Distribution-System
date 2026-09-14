from django.db import models
from django.contrib.auth.models import User


class Notification(models.Model):
    """
    In-app notifications for users regarding donation updates,
    requests, approvals, pickup assignments, and delivery milestones.
    """
    TYPE_CHOICES = [
        ('SYSTEM', 'System Alert'),
        ('REQUEST_RECEIVED', 'Request Received'),
        ('REQUEST_APPROVED', 'Request Approved'),
        ('REQUEST_REJECTED', 'Request Rejected'),
        ('PICKUP_SCHEDULED', 'Pickup Scheduled'),
        ('PICKED_UP', 'Donation Picked Up'),
        ('DELIVERED', 'Donation Delivered'),
        ('COMPLETED', 'Donation Completed'),
        ('ACCOUNT_VERIFIED', 'Account Verified'),
    ]

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    title = models.CharField(
        max_length=150
    )
    message = models.TextField()
    notification_type = models.CharField(
        max_length=50,
        choices=TYPE_CHOICES,
        default='SYSTEM'
    )
    link = models.CharField(
        max_length=255,
        blank=True,
        help_text="Relative URL to navigate upon clicking the notification"
    )
    is_read = models.BooleanField(
        default=False
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.title} ({'Read' if self.is_read else 'Unread'})"
