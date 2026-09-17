from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import Category, DonationCategory, Donation
from .forms import DonationForm, DonationCreateForm
from accounts.decorators import donor_required
from accounts.models import NGOProfile
from core.utils import send_notification


@login_required
def create_donation(request):
    """
    Allows a logged-in user with role == 'DONOR' to post a donation.
    Saves donation with donor=request.user and status='AVAILABLE'.
    """
    profile = getattr(request.user, 'profile', None)
    user_role = getattr(profile, 'role', '').upper() if profile else ''

    if not request.user.is_staff and user_role != 'DONOR':
        messages.error(request, "Access restricted. Only Donors can create donations.")
        return redirect('dashboard:dashboard_home')

    categories = DonationCategory.objects.all()

    if request.method == 'POST':
        form = DonationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    donation = form.save(commit=False)
                    donation.donor = request.user
                    donation.status = 'AVAILABLE'
                    donation.save()

                    # Notify verified NGOs about new available donation
                    verified_ngos = NGOProfile.objects.filter(is_approved=True).select_related('user')
                    for ngo in verified_ngos:
                        send_notification(
                            ngo.user,
                            f"New Donation Available: {donation.title}",
                            f"A new donation of {donation.quantity} is available for request.",
                            "REQUEST_RECEIVED",
                            link=f"/donations/{donation.id}/"
                        )

                    messages.success(request, f"Donation '{donation.title}' was created successfully and is now available for NGOs!")
                    return redirect('donation_detail', pk=donation.id)

            except Exception as e:
                messages.error(request, f"Error saving donation: {str(e)}")
        else:
            messages.error(request, "Please review the form errors below.")
    else:
        initial_data = {}
        if profile and profile.address:
            initial_data['pickup_address'] = profile.address
        form = DonationForm(initial=initial_data)

    context = {
        'form': form,
        'categories': categories,
    }
    return render(request, 'donations/create_donation.html', context)


def check_and_expire_donations():
    """
    Quietly marks past-due available listings as EXPIRED without disruptive errors.
    """
    now = timezone.now()
    Donation.objects.filter(
        status='AVAILABLE',
        expiry_date__isnull=False,
        expiry_date__lt=now
    ).update(status='EXPIRED')


def donation_list(request):
    """
    Browse Donations:
    - Shows all donations where status='AVAILABLE' (running quiet auto-expiry first).
    - Supports filtering by category, search query, delivery_option, city, and hyperlocal match.
    - Allows NGOs to self-filter based on logistics capacity and location.
    """
    check_and_expire_donations()

    donations = Donation.objects.filter(status='AVAILABLE').select_related('category', 'donor', 'donor__profile')

    category_id = request.GET.get('category')
    search_query = request.GET.get('q', '').strip()
    delivery_option = request.GET.get('delivery_option', '').strip()
    city_filter = request.GET.get('city', '').strip()
    hyperlocal_filter = request.GET.get('hyperlocal', '').strip()
    scale_filter = request.GET.get('scale', '').strip()

    # User's city for hyperlocal matching
    user_city = ''
    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        user_city = getattr(profile, 'city', '') or ''

    if category_id:
        donations = donations.filter(category_id=category_id)

    if search_query:
        donations = donations.filter(
            Q(title__icontains=search_query) |
            Q(pickup_address__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(dropoff_location__icontains=search_query)
        )

    if delivery_option in ['DONOR_DELIVERY', 'NGO_PICKUP']:
        donations = donations.filter(delivery_option=delivery_option)

    if city_filter:
        donations = donations.filter(donor__profile__city__icontains=city_filter)

    if hyperlocal_filter == '1' and user_city:
        donations = donations.filter(donor__profile__city__iexact=user_city)

    categories = DonationCategory.objects.all()

    # Scale filter (micro-donations vs standard)
    donation_list_final = []
    if scale_filter == 'micro':
        donation_list_final = [d for d in donations if d.is_small_donation]
    elif scale_filter == 'standard':
        donation_list_final = [d for d in donations if not d.is_small_donation]
    else:
        donation_list_final = list(donations)

    context = {
        'donations': donation_list_final,
        'categories': categories,
        'selected_category': category_id,
        'search_query': search_query,
        'selected_delivery_option': delivery_option,
        'selected_city': city_filter,
        'hyperlocal_active': (hyperlocal_filter == '1'),
        'scale_filter': scale_filter,
        'user_city': user_city,
    }
    return render(request, 'donations/donation_list.html', context)


def donation_detail(request, pk):
    """
    Shows detailed info of a donation.
    - If user is a verified NGO, display an 'Accept & Request Donation' button if status is 'AVAILABLE'.
    - If NGO is not verified (is_verified=False), block requesting and show an info notice:
      'Admin verification required to request items.'
    """
    check_and_expire_donations()

    donation = get_object_or_404(
        Donation.objects.select_related('category', 'donor', 'donor__profile'),
        pk=pk
    )

    user_request = None
    is_ngo = False
    is_verified_ngo = False
    user_city = ''
    is_hyperlocal_match = False

    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        user_role = getattr(profile, 'role', '').upper() if profile else ''
        user_city = getattr(profile, 'city', '') or ''
        if donation.city and user_city and user_city.lower() == donation.city.lower():
            is_hyperlocal_match = True

        if user_role == 'NGO':
            is_ngo = True
            ngo_profile = getattr(request.user, 'ngo_profile', None)
            is_verified_ngo = bool(getattr(profile, 'is_verified', False) or (ngo_profile and ngo_profile.is_approved))
            user_request = donation.requests.filter(ngo=request.user).first()

    approved_request = None
    if donation.status in ['APPROVED', 'COLLECTED', 'COMPLETED']:
        approved_request = donation.requests.filter(
            status__in=['APPROVED', 'COLLECTED', 'COMPLETED']
        ).select_related('ngo', 'ngo__profile', 'ngo__ngo_profile').first()

    context = {
        'donation': donation,
        'user_request': user_request,
        'approved_request': approved_request,
        'is_ngo': is_ngo,
        'is_verified_ngo': is_verified_ngo,
        'user_city': user_city,
        'is_hyperlocal_match': is_hyperlocal_match,
    }
    return render(request, 'donations/donation_detail.html', context)


@login_required
def my_donations(request):
    """
    Shows donations created by the currently logged-in donor with current statuses.
    """
    profile = getattr(request.user, 'profile', None)
    user_role = getattr(profile, 'role', '').upper() if profile else ''

    if not request.user.is_staff and user_role != 'DONOR':
        messages.error(request, "Only Donors can view their listed donations.")
        return redirect('dashboard:dashboard_home')

    donations = Donation.objects.filter(donor=request.user).select_related('category').order_by('-created_at')

    status_filter = request.GET.get('status', 'ALL')
    if status_filter != 'ALL':
        donations = donations.filter(status=status_filter)

    context = {
        'donations': donations,
        'status_filter': status_filter,
    }
    return render(request, 'donations/my_donations.html', context)


@login_required
def cancel_donation(request, pk):
    """
    Allows donor to cancel a donation if not yet collected or completed.
    """
    donation = get_object_or_404(Donation, pk=pk, donor=request.user)

    if donation.status in ['COLLECTED', 'COMPLETED']:
        messages.error(request, "This donation cannot be cancelled because it is already collected or completed.")
    else:
        donation.change_status(
            'CANCELLED',
            user=request.user,
            remarks="Cancelled by donor."
        )
        messages.info(request, f"Donation '{donation.title}' has been cancelled.")

    return redirect('my_donations')
