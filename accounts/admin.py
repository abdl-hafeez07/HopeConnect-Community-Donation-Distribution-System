from django.contrib import admin
from django.utils import timezone
from .models import UserProfile, NGOProfile, VolunteerProfile

admin.site.site_header = "HopeConnect Administration"
admin.site.site_title = "HopeConnect Admin Portal"
admin.site.index_title = "HopeConnect Management & System Reports"


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'role',
        'phone',
        'city',
        'is_verified',
        'created_at',
    )
    list_filter = (
        'role',
        'is_verified',
        'city',
    )
    search_fields = (
        'user__username',
        'user__email',
        'phone',
        'city',
    )
    actions = ['mark_as_verified']

    @admin.action(description="Mark selected profiles as verified")
    def mark_as_verified(self, request, queryset):
        queryset.update(is_verified=True)


@admin.register(NGOProfile)
class NGOProfileAdmin(admin.ModelAdmin):
    list_display = (
        'organization_name',
        'user',
        'registration_number',
        'contact_person',
        'is_approved',
        'verified_by',
        'verified_at',
    )
    list_filter = (
        'is_approved',
    )
    search_fields = (
        'organization_name',
        'registration_number',
        'contact_person',
        'user__username',
    )
    actions = ['approve_ngos']

    @admin.action(description="Approve selected NGOs")
    def approve_ngos(self, request, queryset):
        queryset.update(
            is_approved=True,
            verified_at=timezone.now(),
            verified_by=request.user
        )
        for ngo in queryset:
            if hasattr(ngo.user, 'profile'):
                ngo.user.profile.is_verified = True
                ngo.user.profile.save()


@admin.register(VolunteerProfile)
class VolunteerProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'vehicle_type',
        'availability_status',
        'is_approved',
        'verified_by',
        'verified_at',
    )
    list_filter = (
        'is_approved',
        'vehicle_type',
        'availability_status',
    )
    search_fields = (
        'user__username',
        'user__email',
    )
    actions = ['approve_volunteers']

    @admin.action(description="Approve selected Volunteers")
    def approve_volunteers(self, request, queryset):
        queryset.update(
            is_approved=True,
            verified_at=timezone.now(),
            verified_by=request.user
        )
        for vol in queryset:
            if hasattr(vol.user, 'profile'):
                vol.user.profile.is_verified = True
                vol.user.profile.save()