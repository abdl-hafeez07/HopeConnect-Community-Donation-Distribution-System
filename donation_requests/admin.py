from django.contrib import admin
from .models import DonationRequest


@admin.register(DonationRequest)
class DonationRequestAdmin(admin.ModelAdmin):
    list_display = (
        'donation',
        'ngo',
        'status',
        'created_at',
        'updated_at',
    )
    list_filter = (
        'status',
        'created_at',
    )
    search_fields = (
        'donation__title',
        'ngo__username',
        'message',
    )
