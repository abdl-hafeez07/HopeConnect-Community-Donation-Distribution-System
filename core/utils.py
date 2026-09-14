from core.models import Notification


def send_notification(recipient, title, message, notification_type='SYSTEM', link=''):
    """
    Utility function to create and dispatch an in-app notification to a user.
    """
    if recipient and recipient.is_authenticated:
        return Notification.objects.create(
            recipient=recipient,
            title=title,
            message=message,
            notification_type=notification_type,
            link=link
        )
    return None
