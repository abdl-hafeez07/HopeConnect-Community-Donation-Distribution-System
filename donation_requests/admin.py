from django.contrib import admin
from .models import DonationRequest, DeliveryAssignment


@admin.register(DonationRequest)
class DonationRequestAdmin(admin.ModelAdmin):
    list_display = (
        'donation',
        'ngo',
        'beneficiaries_count',
        'status',
        'requested_at',
        'responded_at',
    )
    list_filter = (
        'status',
        'requested_at',
    )
    search_fields = (
        'donation__title',
        'ngo__username',
        'message',
    )


@admin.register(DeliveryAssignment)
class DeliveryAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        'donation',
        'request',
        'volunteer',
        'status',
        'scheduled_pickup_time',
        'delivered_at',
    )
    list_filter = (
        'status',
        'created_at',
    )
    search_fields = (
        'donation__title',
        'volunteer__username',
        'recipient_confirmation_name',
    )
