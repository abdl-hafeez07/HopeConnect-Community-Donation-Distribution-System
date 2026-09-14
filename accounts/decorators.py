from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def role_required(*allowed_roles):
    """
    Decorator that checks if the logged-in user belongs to one of the specified roles.
    Admins (is_staff or role='Admin') are granted access universally.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, "Please log in to access this page.")
                return redirect('login')

            profile = getattr(request.user, 'profile', None)
            user_role = profile.role if profile else ('Admin' if request.user.is_staff else None)

            if request.user.is_staff or user_role == 'Admin' or (user_role in allowed_roles):
                return view_func(request, *args, **kwargs)

            messages.error(request, f"Access restricted. This page is only accessible by {', '.join(allowed_roles)}.")
            return redirect('dashboard_home')

        return _wrapped_view
    return decorator


def donor_required(view_func):
    return role_required('Donor')(view_func)


def ngo_required(view_func):
    return role_required('NGO')(view_func)


def volunteer_required(view_func):
    return role_required('Volunteer')(view_func)


def admin_required(view_func):
    return role_required('Admin')(view_func)


def verified_ngo_required(view_func):
    """
    Checks that the user is an NGO and has been approved/verified by an administrator.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')

        profile = getattr(request.user, 'profile', None)
        if not profile or profile.role != 'NGO':
            messages.error(request, "Only registered NGOs can perform this action.")
            return redirect('dashboard_home')

        ngo_profile = getattr(request.user, 'ngo_profile', None)
        if not (ngo_profile and ngo_profile.is_approved):
            messages.warning(
                request,
                "Your NGO account is currently pending verification by our administration team. "
                "Once verified, you will be able to request donations."
            )
            return redirect('ngo_dashboard')

        return view_func(request, *args, **kwargs)

    return _wrapped_view
