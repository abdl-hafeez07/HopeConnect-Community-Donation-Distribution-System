from django.contrib import admin
from .models import DonationRequest


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
