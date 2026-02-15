"""
Notification model for in-app notifications.
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from apps.common.models import TimestampedModel

User = get_user_model()


class NotificationType(models.TextChoices):
    """Notification type choices."""

    # Issue notifications
    ISSUE_CREATED = 'issue_created', _('Issue Created')
    ISSUE_UPDATED = 'issue_updated', _('Issue Updated')
    ISSUE_ASSIGNED = 'issue_assigned', _('Issue Assigned')
    ISSUE_COMMENTED = 'issue_commented', _('Issue Commented')
    ISSUE_TRANSITIONED = 'issue_transitioned', _('Issue Transitioned')
    ISSUE_MENTIONED = 'issue_mentioned', _('Mentioned in Issue')

    # Sprint notifications
    SPRINT_STARTED = 'sprint_started', _('Sprint Started')
    SPRINT_COMPLETED = 'sprint_completed', _('Sprint Completed')
    SPRINT_ISSUE_ADDED = 'sprint_issue_added', _('Issue Added to Sprint')

    # Project notifications
    PROJECT_MEMBER_ADDED = 'project_member_added', _('Added to Project')
    PROJECT_MEMBER_REMOVED = 'project_member_removed', _('Removed from Project')

    # Automation notifications
    AUTOMATION_EXECUTED = 'automation_executed', _('Automation Rule Executed')

    # System notifications
    SYSTEM_ANNOUNCEMENT = 'system_announcement', _('System Announcement')


class NotificationQuerySet(models.QuerySet):
    """Custom QuerySet for Notification."""

    def unread(self):
        """Filter unread notifications only."""
        return self.filter(read_at__isnull=True)

    def read(self):
        """Filter read notifications only."""
        return self.filter(read_at__isnull=False)

    def for_user(self, user):
        """Filter notifications for a specific user."""
        return self.filter(recipient=user)

    def for_organization(self, organization):
        """Filter notifications for an organization."""
        return self.filter(organization=organization)

    def by_type(self, notification_type):
        """Filter by notification type."""
        return self.filter(notification_type=notification_type)

    def recent(self, limit=20):
        """Get recent notifications."""
        return self.order_by('-created_at')[:limit]

    def mark_all_read(self):
        """Mark all notifications as read."""
        return self.update(read_at=timezone.now())


class Notification(TimestampedModel):
    """
    In-app notification model.

    Stores notifications for users about various events in the system.
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
        related_name='notifications',
        help_text=_('Organization this notification belongs to')
    )

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text=_('User who receives this notification')
    )

    actor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='triggered_notifications',
        help_text=_('User who triggered this notification')
    )

    notification_type = models.CharField(
        max_length=50,
        choices=NotificationType.choices,
        db_index=True,
        verbose_name=_('notification type'),
        help_text=_('Type of notification')
    )

    title = models.CharField(
        max_length=255,
        verbose_name=_('title'),
        help_text=_('Notification title')
    )

    message = models.TextField(
        verbose_name=_('message'),
        help_text=_('Notification message')
    )

    # Related entities
    issue = models.ForeignKey(
        'issues.Issue',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        help_text=_('Related issue')
    )

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        help_text=_('Related project')
    )

    sprint = models.ForeignKey(
        'boards.Sprint',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        help_text=_('Related sprint')
    )

    # Metadata
    data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('data'),
        help_text=_('Additional notification data')
    )

    # Action URL (for deep linking)
    action_url = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_('action URL'),
        help_text=_('URL to navigate when notification is clicked')
    )

    # Read status
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('read at'),
        help_text=_('When this notification was read')
    )

    # Email status
    email_sent = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=_('email sent'),
        help_text=_('Whether email notification was sent')
    )

    email_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('email sent at'),
        help_text=_('When email notification was sent')
    )

    objects = NotificationQuerySet.as_manager()

    class Meta:
        db_table = 'notifications'
        verbose_name = _('notification')
        verbose_name_plural = _('notifications')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['recipient', 'read_at']),
            models.Index(fields=['organization', '-created_at']),
            models.Index(fields=['notification_type', '-created_at']),
            models.Index(fields=['issue', '-created_at']),
        ]

    def __str__(self):
        return f"{self.notification_type} for {self.recipient.email}"

    def mark_as_read(self):
        """Mark notification as read."""
        if not self.read_at:
            self.read_at = timezone.now()
            self.save(update_fields=['read_at'])

    def mark_as_unread(self):
        """Mark notification as unread."""
        if self.read_at:
            self.read_at = None
            self.save(update_fields=['read_at'])

    @property
    def is_read(self) -> bool:
        """Check if notification is read."""
        return self.read_at is not None

    def mark_email_sent(self):
        """Mark email as sent."""
        if not self.email_sent:
            self.email_sent = True
            self.email_sent_at = timezone.now()
            self.save(update_fields=['email_sent', 'email_sent_at'])

    def get_display_text(self) -> str:
        """Get formatted display text for notification."""
        actor_name = self.actor.get_full_name() or self.actor.email if self.actor else 'Someone'

        if self.notification_type == NotificationType.ISSUE_CREATED:
            return f"{actor_name} created issue {self.issue.key}"
        elif self.notification_type == NotificationType.ISSUE_ASSIGNED:
            return f"{actor_name} assigned issue {self.issue.key} to you"
        elif self.notification_type == NotificationType.ISSUE_COMMENTED:
            return f"{actor_name} commented on {self.issue.key}"
        elif self.notification_type == NotificationType.ISSUE_MENTIONED:
            return f"{actor_name} mentioned you in {self.issue.key}"
        elif self.notification_type == NotificationType.SPRINT_STARTED:
            return f"Sprint '{self.sprint.name}' has started"
        elif self.notification_type == NotificationType.SPRINT_COMPLETED:
            return f"Sprint '{self.sprint.name}' has been completed"

        return self.message
