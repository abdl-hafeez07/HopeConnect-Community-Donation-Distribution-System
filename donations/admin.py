from django.contrib import admin
from .models import DonationCategory, Donation


@admin.register(DonationCategory)
class DonationCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'donor',
        'category',
        'quantity',
        'status',
        'pickup_date',
        'created_at',
    )
    list_filter = (
        'status',
        'category',
        'pickup_date',
        'created_at',
    )
    search_fields = (
        'title',
        'description',
        'donor__username',
        'pickup_address',
    )
