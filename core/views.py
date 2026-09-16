from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Notification
from donations.models import Donation, Category


def home(request):
    recent_donations = Donation.objects.filter(status='AVAILABLE').select_related('category', 'donor')[:6]
    categories = Category.objects.all()
    return render(request, 'index.html', {'recent_donations': recent_donations, 'categories': categories})


def about(request):
    return render(request, 'about.html')


def services(request):
    return render(request, 'services.html')


def contact(request):
    return render(request, 'contact.html')


@login_required
def notifications_list(request):
    """
    Displays list of all notifications for logged in user.
    """
    notifications = request.user.notifications.all().order_by('-created_at')
    # Mark all as read when user visits notifications page
    unread = notifications.filter(is_read=False)
    unread.update(is_read=True)

    return render(request, 'core/notifications.html', {'notifications': notifications})


@login_required
def mark_notification_read(request, pk):
    """
    Marks individual notification as read and navigates to target link.
    """
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notif.is_read = True
    notif.save()
    if notif.link:
        return redirect(notif.link)
    return redirect('notifications_list')