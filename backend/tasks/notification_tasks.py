"""
Celery tasks for notifications.
"""

from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_notification_email(notification_id: str):
    """
    Send email notification asynchronously.

    Args:
        notification_id: Notification ID to send
    """
    from apps.notifications.models import Notification
    from apps.notifications.services import EmailService

    try:
        notification = Notification.objects.get(id=notification_id)
        EmailService.send_notification_email(notification)
        logger.info(f"Email notification sent for {notification_id}")
    except Notification.DoesNotExist:
        logger.error(f"Notification {notification_id} not found")
    except Exception as e:
        logger.error(f"Failed to send email notification {notification_id}: {str(e)}")


@shared_task
def send_digest_emails():
    """
    Send digest emails to users who have digest enabled.

    Runs on schedule (daily or weekly).
    """
    from django.contrib.auth import get_user_model
    from apps.notifications.models import Notification, NotificationPreference
    from apps.notifications.services import EmailService
    from django.utils import timezone
    from datetime import timedelta

    User = get_user_model()

    # Get users with digest enabled
    preferences = NotificationPreference.objects.filter(
        email_digest_enabled=True,
        email_digest_frequency__in=['daily', 'weekly'],
    ).select_related('user', 'organization')

    for preference in preferences:
        try:
            # Determine time range based on frequency
            if preference.email_digest_frequency == 'daily':
                since = timezone.now() - timedelta(days=1)
            else:  # weekly
                since = timezone.now() - timedelta(weeks=1)

            # Get unsent notifications
            notifications = Notification.objects.filter(
                recipient=preference.user,
                organization=preference.organization,
                email_sent=False,
                created_at__gte=since,
            ).order_by('-created_at')

            if notifications.exists():
                EmailService.send_digest_email(preference.user, list(notifications))
                logger.info(f"Digest email sent to {preference.user.email}")

        except Exception as e:
            logger.error(f"Failed to send digest to {preference.user.email}: {str(e)}")


@shared_task
def cleanup_old_notifications(days=90):
    """
    Clean up old read notifications.

    Args:
        days: Number of days to keep notifications
    """
    from apps.notifications.models import Notification
    from django.utils import timezone
    from datetime import timedelta

    cutoff_date = timezone.now() - timedelta(days=days)

    # Delete old read notifications
    deleted_count = Notification.objects.filter(
        read_at__isnull=False,
        read_at__lt=cutoff_date,
    ).delete()[0]

    logger.info(f"Cleaned up {deleted_count} old notifications")
    return deleted_count
