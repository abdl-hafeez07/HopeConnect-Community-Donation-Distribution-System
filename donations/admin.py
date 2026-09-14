from django.contrib import admin
from .models import Category, Donation, FoodDetail, DonationStatusHistory


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')


class FoodDetailInline(admin.StackedInline):
    model = FoodDetail
    can_delete = False
    extra = 0


class DonationStatusHistoryInline(admin.TabularInline):
    model = DonationStatusHistory
    extra = 0
    readonly_fields = ('status', 'changed_by', 'remarks', 'timestamp')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'donor',
        'category',
        'quantity',
        'city',
        'status',
        'created_at',
    )
    list_filter = (
        'status',
        'category',
        'city',
        'created_at',
    )
    search_fields = (
        'title',
        'description',
        'donor__username',
        'city',
        'pickup_address',
    )
    inlines = [FoodDetailInline, DonationStatusHistoryInline]


@admin.register(FoodDetail)
class FoodDetailAdmin(admin.ModelAdmin):
    list_display = (
        'donation',
        'food_type',
        'dietary_type',
        'expiry_time',
        'is_expired',
    )
    list_filter = (
        'food_type',
        'dietary_type',
    )
    search_fields = (
        'donation__title',
        'storage_instructions',
    )


@admin.register(DonationStatusHistory)
class DonationStatusHistoryAdmin(admin.ModelAdmin):
    list_display = (
        'donation',
        'status',
        'changed_by',
        'timestamp',
    )
    list_filter = ('status', 'timestamp')
    search_fields = ('donation__title', 'remarks')
