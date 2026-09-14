from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import transaction

from .forms import UserRegisterForm, UserLoginForm, UserProfileUpdateForm
from .models import UserProfile, NGOProfile, VolunteerProfile
from core.utils import send_notification


def register_view(request):
    """
    Handles user signup with role selection (Donor, NGO, Volunteer).
    Automatically creates the associated UserProfile and role-specific profile.
    """
    if request.user.is_authenticated:
        return redirect('dashboard_home')

    if request.method == 'POST':
        form = UserRegisterForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # 1. Create User
                    user = User.objects.create_user(
                        username=form.cleaned_data['username'],
                        email=form.cleaned_data['email'],
                        password=form.cleaned_data['password']
                    )

                    role = form.cleaned_data['role']
                    is_auto_verified = (role == 'Donor')

                    # 2. Create UserProfile
                    profile = UserProfile.objects.create(
                        user=user,
                        role=role,
                        phone=form.cleaned_data.get('phone', ''),
                        address=form.cleaned_data.get('address', ''),
                        city=form.cleaned_data.get('city', ''),
                        is_verified=is_auto_verified
                    )

                    # 3. Create Role-Specific Profile
                    if role == 'NGO':
                        NGOProfile.objects.create(
                            user=user,
                            organization_name=form.cleaned_data.get('organization_name', ''),
                            registration_number=form.cleaned_data.get('registration_number', ''),
                            contact_person=form.cleaned_data.get('contact_person', ''),
                            website=form.cleaned_data.get('website', ''),
                            mission=form.cleaned_data.get('mission', ''),
                            verification_document=form.cleaned_data.get('verification_document')
                        )
                        send_notification(
                            user,
                            "Registration Submitted",
                            "Welcome to HopeConnect! Your NGO registration has been received and is pending admin verification.",
                            "ACCOUNT_VERIFIED"
                        )
                    elif role == 'Volunteer':
                        VolunteerProfile.objects.create(
                            user=user,
                            vehicle_type=form.cleaned_data.get('vehicle_type', 'None/Walking'),
                            id_proof_document=form.cleaned_data.get('id_proof_document')
                        )
                        send_notification(
                            user,
                            "Welcome to the Volunteer Network",
                            "Thank you for signing up to volunteer! Our coordinators will verify your account shortly.",
                            "ACCOUNT_VERIFIED"
                        )
                    else:
                        send_notification(
                            user,
                            "Welcome to HopeConnect!",
                            "You are now ready to make a difference by sharing surplus food and essentials.",
                            "SYSTEM"
                        )

                    # 4. Log in immediately
                    auth_login(request, user)
                    messages.success(request, f"Welcome to HopeConnect, {user.username}! Your account has been created.")
                    return redirect('dashboard_home')

            except Exception as e:
                messages.error(request, f"An error occurred during registration: {str(e)}")
    else:
        # Check if pre-selected role in GET query
        initial_role = request.GET.get('role', 'Donor')
        if initial_role not in ['Donor', 'NGO', 'Volunteer']:
            initial_role = 'Donor'
        form = UserRegisterForm(initial={'role': initial_role})

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    """
    Standard user authentication view with role-aware redirection.
    """
    if request.user.is_authenticated:
        return redirect('dashboard_home')

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('dashboard_home')
        else:
            messages.error(request, "Invalid username or password. Please try again.")
    else:
        form = UserLoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """
    Logs out user and redirects to home page.
    """
    auth_logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('home')


@login_required
def profile_view(request):
    """
    Allows user to inspect and edit contact information and profile picture.
    """
    profile = getattr(request.user, 'profile', None)
    if not profile:
        profile = UserProfile.objects.create(user=request.user, role='Donor')

    if request.method == 'POST':
        form = UserProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            request.user.email = form.cleaned_data['email']
            request.user.save()
            form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect('profile')
    else:
        form = UserProfileUpdateForm(instance=profile, initial={'email': request.user.email})

    context = {
        'profile': profile,
        'form': form,
    }
    return render(request, 'accounts/profile.html', context)
