def hopeconnect_context(request):
    """
    Context processor to make user profile, role, and unread notification count
    globally available across all templates.
    """
    context = {
        'user_profile': None,
        'user_role': None,
        'unread_notifications_count': 0,
    }

    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        context['user_profile'] = profile
        if profile:
            context['user_role'] = profile.role
        elif request.user.is_staff:
            context['user_role'] = 'Admin'

        context['unread_notifications_count'] = request.user.notifications.filter(is_read=False).count()

    return context
