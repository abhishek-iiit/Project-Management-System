"""
Notification preference model for user notification settings.
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimestampedModel

User = get_user_model()


class NotificationChannel(models.TextChoices):
    """Notification channel choices."""

    IN_APP = 'in_app', _('In-App')
    EMAIL = 'email', _('Email')
    PUSH = 'push', _('Push Notification')


class NotificationPreferenceQuerySet(models.QuerySet):
    """Custom QuerySet for NotificationPreference."""

    def for_user(self, user):
        """Filter preferences for a specific user."""
        return self.filter(user=user)

    def for_organization(self, organization):
        """Filter preferences for an organization."""
        return self.filter(organization=organization)

    def enabled(self):
        """Filter enabled preferences only."""
        return self.filter(is_enabled=True)


class NotificationPreference(TimestampedModel):
    """
    User notification preference model.

    Controls which notifications a user receives and through which channels.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text=_('Unique identifier (UUID4)')
    )

    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='notification_preferences',
        help_text=_('Organization these preferences belong to')
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
        help_text=_('User who owns these preferences')
    )

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notification_preferences',
        help_text=_('Project-specific preferences (null for global)')
    )

    # Global settings
    is_enabled = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_('is enabled'),
        help_text=_('Master switch for all notifications')
    )

    # Channel preferences
    in_app_enabled = models.BooleanField(
        default=True,
        verbose_name=_('in-app enabled'),
        help_text=_('Receive in-app notifications')
    )

    email_enabled = models.BooleanField(
        default=True,
        verbose_name=_('email enabled'),
        help_text=_('Receive email notifications')
    )

    push_enabled = models.BooleanField(
        default=False,
        verbose_name=_('push enabled'),
        help_text=_('Receive push notifications')
    )

    # Email settings
    email_digest_enabled = models.BooleanField(
        default=False,
        verbose_name=_('email digest enabled'),
        help_text=_('Receive digest emails instead of individual emails')
    )

    email_digest_frequency = models.CharField(
        max_length=20,
        choices=[
            ('daily', _('Daily')),
            ('weekly', _('Weekly')),
            ('never', _('Never')),
        ],
        default='daily',
        verbose_name=_('email digest frequency'),
        help_text=_('How often to send digest emails')
    )

    # Event-specific preferences (JSONB for flexibility)
    event_preferences = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('event preferences'),
        help_text=_('Per-event notification preferences')
    )

    # Example event_preferences structure:
    # {
    #     "issue_created": {"in_app": True, "email": True, "push": False},
    #     "issue_assigned": {"in_app": True, "email": True, "push": True},
    #     "issue_commented": {"in_app": True, "email": False, "push": False},
    #     ...
    # }

    # Do Not Disturb
    dnd_enabled = models.BooleanField(
        default=False,
        verbose_name=_('do not disturb'),
        help_text=_('Temporarily disable all notifications')
    )

    dnd_until = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('do not disturb until'),
        help_text=_('When to re-enable notifications')
    )

    # Mention preferences
    notify_on_mention = models.BooleanField(
        default=True,
        verbose_name=_('notify on mention'),
        help_text=_('Receive notifications when mentioned')
    )

    # Watching preferences
    notify_on_watched_issue_update = models.BooleanField(
        default=True,
        verbose_name=_('notify on watched issue update'),
        help_text=_('Receive notifications for watched issues')
    )

    objects = NotificationPreferenceQuerySet.as_manager()

    class Meta:
        db_table = 'notification_preferences'
        verbose_name = _('notification preference')
        verbose_name_plural = _('notification preferences')
        ordering = ['user', 'organization']
        unique_together = [
            ['user', 'organization', 'project'],
        ]
        indexes = [
            models.Index(fields=['user', 'organization']),
            models.Index(fields=['organization', 'is_enabled']),
        ]

    def __str__(self):
        scope = f"Project: {self.project.name}" if self.project else "Global"
        return f"{self.user.email} - {scope}"

    def is_channel_enabled(self, channel: str) -> bool:
        """
        Check if a notification channel is enabled.

        Args:
            channel: Channel name ('in_app', 'email', 'push')

        Returns:
            True if channel is enabled, False otherwise
        """
        if not self.is_enabled:
            return False

        if self.dnd_enabled:
            from django.utils import timezone
            if not self.dnd_until or timezone.now() < self.dnd_until:
                return False

        if channel == NotificationChannel.IN_APP:
            return self.in_app_enabled
        elif channel == NotificationChannel.EMAIL:
            return self.email_enabled
        elif channel == NotificationChannel.PUSH:
            return self.push_enabled

        return False

    def is_event_enabled(self, event_type: str, channel: str = 'in_app') -> bool:
        """
        Check if notifications are enabled for a specific event and channel.

        Args:
            event_type: Notification event type
            channel: Channel name ('in_app', 'email', 'push')

        Returns:
            True if event notifications are enabled, False otherwise
        """
        if not self.is_channel_enabled(channel):
            return False

        # Check event-specific preferences
        if event_type in self.event_preferences:
            event_pref = self.event_preferences[event_type]
            return event_pref.get(channel, True)

        # Default to enabled if not specifically configured
        return True

    def set_event_preference(self, event_type: str, in_app: bool = True, email: bool = True, push: bool = False):
        """
        Set notification preferences for a specific event.

        Args:
            event_type: Notification event type
            in_app: Enable in-app notifications
            email: Enable email notifications
            push: Enable push notifications
        """
        if not self.event_preferences:
            self.event_preferences = {}

        self.event_preferences[event_type] = {
            'in_app': in_app,
            'email': email,
            'push': push,
        }
        self.save(update_fields=['event_preferences'])

    @classmethod
    def get_or_create_for_user(cls, user, organization, project=None):
        """
        Get or create notification preferences for a user.

        Args:
            user: User instance
            organization: Organization instance
            project: Optional project instance

        Returns:
            NotificationPreference instance
        """
        preference, created = cls.objects.get_or_create(
            user=user,
            organization=organization,
            project=project,
            defaults={
                'is_enabled': True,
                'in_app_enabled': True,
                'email_enabled': True,
                'push_enabled': False,
            }
        )
        return preference
