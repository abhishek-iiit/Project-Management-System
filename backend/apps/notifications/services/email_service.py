"""
Email service for sending notification emails.
"""

import logging
from typing import Dict, List, Optional
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags

from apps.notifications.models import Notification, NotificationPreference

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending notification emails."""

    @staticmethod
    def send_notification_email(notification: Notification) -> bool:
        """
        Send email for a notification.

        Args:
            notification: Notification to send via email

        Returns:
            True if email was sent successfully, False otherwise
        """
        try:
            # Check if user wants email notifications
            preference = NotificationPreference.get_or_create_for_user(
                user=notification.recipient,
                organization=notification.organization,
                project=notification.project,
            )

            if not preference.email_enabled:
                logger.info(f"Email notifications disabled for {notification.recipient.email}")
                return False

            # Don't send if user prefers digest
            if preference.email_digest_enabled and preference.email_digest_frequency != 'never':
                logger.info(f"User {notification.recipient.email} prefers digest emails")
                return False

            # Prepare email content
            subject = notification.title
            context = {
                'notification': notification,
                'recipient': notification.recipient,
                'actor': notification.actor,
                'issue': notification.issue,
                'project': notification.project,
                'sprint': notification.sprint,
                'action_url': EmailService._get_absolute_url(notification.action_url),
                'organization': notification.organization,
            }

            # Render HTML email
            html_message = render_to_string(
                'email/notification.html',
                context
            )

            # Create plain text version
            text_message = strip_tags(html_message)

            # Send email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[notification.recipient.email],
            )
            email.attach_alternative(html_message, "text/html")
            email.send()

            # Mark notification as email sent
            notification.mark_email_sent()

            logger.info(f"Email notification sent to {notification.recipient.email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}")
            return False

    @staticmethod
    def send_digest_email(user, notifications: List[Notification]) -> bool:
        """
        Send digest email with multiple notifications.

        Args:
            user: User to send digest to
            notifications: List of notifications to include

        Returns:
            True if email was sent successfully, False otherwise
        """
        try:
            if not notifications:
                logger.info(f"No notifications to send in digest for {user.email}")
                return False

            # Group notifications by type
            grouped_notifications = {}
            for notification in notifications:
                if notification.notification_type not in grouped_notifications:
                    grouped_notifications[notification.notification_type] = []
                grouped_notifications[notification.notification_type].append(notification)

            # Prepare email content
            subject = f"You have {len(notifications)} new notifications"
            context = {
                'user': user,
                'notifications': notifications,
                'grouped_notifications': grouped_notifications,
                'total_count': len(notifications),
            }

            # Render HTML email
            html_message = render_to_string(
                'email/digest.html',
                context
            )

            # Create plain text version
            text_message = strip_tags(html_message)

            # Send email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )
            email.attach_alternative(html_message, "text/html")
            email.send()

            # Mark all notifications as email sent
            for notification in notifications:
                notification.mark_email_sent()

            logger.info(f"Digest email sent to {user.email} with {len(notifications)} notifications")
            return True

        except Exception as e:
            logger.error(f"Failed to send digest email: {str(e)}")
            return False

    @staticmethod
    def send_custom_email(
        to_email: str,
        subject: str,
        message: str,
        html_message: Optional[str] = None,
    ) -> bool:
        """
        Send a custom email.

        Args:
            to_email: Recipient email address
            subject: Email subject
            message: Plain text message
            html_message: Optional HTML message

        Returns:
            True if email was sent successfully, False otherwise
        """
        try:
            if html_message:
                email = EmailMultiAlternatives(
                    subject=subject,
                    body=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[to_email],
                )
                email.attach_alternative(html_message, "text/html")
                email.send()
            else:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[to_email],
                    fail_silently=False,
                )

            logger.info(f"Custom email sent to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send custom email: {str(e)}")
            return False

    @staticmethod
    def _get_absolute_url(path: str) -> str:
        """
        Convert relative URL to absolute URL.

        Args:
            path: Relative URL path

        Returns:
            Absolute URL
        """
        if not path:
            return ''

        # Get base URL from settings
        base_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        if path.startswith('/'):
            return f"{base_url}{path}"
        return f"{base_url}/{path}"
