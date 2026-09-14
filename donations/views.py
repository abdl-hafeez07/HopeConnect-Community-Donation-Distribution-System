from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q

from .models import Category, Donation, FoodDetail, DonationStatusHistory
from .forms import DonationCreateForm, FoodDetailForm
from accounts.decorators import donor_required
from accounts.models import NGOProfile
from core.utils import send_notification


@login_required
@donor_required
def create_donation(request):
    """
    Form allowing registered donors to list surplus food or essentials.
    Dynamically binds FoodDetail when a food-related category is chosen.
    """
    categories = Category.objects.filter(is_active=True)
    food_category_ids = list(Category.objects.filter(
        Q(name__icontains='food') | Q(name__icontains='meal') | Q(name__icontains='grocer')
    ).values_list('id', flat=True))

    if request.method == 'POST':
        form = DonationCreateForm(request.POST, request.FILES)
        food_form = FoodDetailForm(request.POST)

        category_id = request.POST.get('category')
        is_food_category = int(category_id) in food_category_ids if (category_id and category_id.isdigit()) else False

        if form.is_valid() and (not is_food_category or food_form.is_valid()):
            try:
                with transaction.atomic():
                    donation = form.save(commit=False)
                    donation.donor = request.user
                    donation.status = Donation.STATUS_AVAILABLE
                    donation.save()

                    if is_food_category and food_form.is_valid():
                        food_detail = food_form.save(commit=False)
                        food_detail.donation = donation
                        food_detail.save()

                    # Record initial audit entry
                    DonationStatusHistory.objects.create(
                        donation=donation,
                        status=Donation.STATUS_AVAILABLE,
                        changed_by=request.user,
                        remarks="Donation posted by donor."
                    )

                    # Notify verified NGOs in the system
                    verified_ngos = NGOProfile.objects.filter(is_approved=True).select_related('user')
                    for ngo in verified_ngos:
                        send_notification(
                            ngo.user,
                            f"New Donation Available: {donation.title}",
                            f"A new donation of {donation.quantity} in {donation.city} is available for request.",
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
        # Prepopulate donor address/city from profile
        profile = getattr(request.user, 'profile', None)
        initial_data = {}
        if profile:
            initial_data['city'] = profile.city
            initial_data['pickup_address'] = profile.address
        form = DonationCreateForm(initial=initial_data)
        food_form = FoodDetailForm()

    context = {
        'form': form,
        'food_form': food_form,
        'categories': categories,
        'food_category_ids': food_category_ids,
    }
    return render(request, 'donations/create_donation.html', context)


def donation_list(request):
    """
    Public and NGO catalog to search and filter available donations.
    """
    donations = Donation.objects.filter(status=Donation.STATUS_AVAILABLE).select_related('category', 'donor')

    category_id = request.GET.get('category')
    city = request.GET.get('city')
    search_query = request.GET.get('q')

    if category_id:
        donations = donations.filter(category_id=category_id)
    if city:
        donations = donations.filter(city__icontains=city)
    if search_query:
        donations = donations.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(city__icontains=search_query)
        )

    categories = Category.objects.filter(is_active=True)

    context = {
        'donations': donations,
        'categories': categories,
        'selected_category': category_id,
        'selected_city': city,
        'search_query': search_query,
    }
    return render(request, 'donations/donation_list.html', context)


def donation_detail(request, pk):
    """
    Detailed inspection page for a donation: items, food details, current status,
    and the complete audit status history.
    """
    donation = get_object_or_404(
        Donation.objects.select_related('category', 'donor', 'donor__profile'),
        pk=pk
    )
    food_detail = getattr(donation, 'food_detail', None)
    status_history = donation.status_history.select_related('changed_by').order_by('-timestamp')

    # Check if current user is an NGO that has requested this donation
    user_request = None
    if request.user.is_authenticated:
        user_request = donation.requests.filter(ngo=request.user).first()

    # Delivery info if assigned
    delivery_assignment = getattr(donation, 'delivery', None)

    context = {
        'donation': donation,
        'food_detail': food_detail,
        'status_history': status_history,
        'user_request': user_request,
        'delivery_assignment': delivery_assignment,
    }
    return render(request, 'donations/donation_detail.html', context)


@login_required
@donor_required
def my_donations(request):
    """
    Lists all donations posted by the logged-in donor.
    """
    status_filter = request.GET.get('status', 'ALL')
    donations = Donation.objects.filter(donor=request.user).select_related('category')

    if status_filter != 'ALL':
        donations = donations.filter(status=status_filter)

    context = {
        'donations': donations.order_by('-created_at'),
        'status_filter': status_filter,
    }
    return render(request, 'donations/my_donations.html', context)


@login_required
@donor_required
def cancel_donation(request, pk):
    """
    Allows donor to cancel a donation if not yet picked up.
    """
    donation = get_object_or_404(Donation, pk=pk, donor=request.user)

    if donation.status in [Donation.STATUS_PICKED_UP, Donation.STATUS_DELIVERED, Donation.STATUS_COMPLETED]:
        messages.error(request, "This donation cannot be cancelled because it is already in transit or completed.")
    else:
        donation.change_status(
            Donation.STATUS_CANCELLED,
            user=request.user,
            remarks="Cancelled by donor."
        )
        messages.info(request, f"Donation '{donation.title}' has been cancelled.")

    return redirect('my_donations')
