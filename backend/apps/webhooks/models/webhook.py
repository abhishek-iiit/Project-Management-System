"""
Webhook model for outgoing webhooks.
"""

import uuid
import secrets
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimestampedModel, SoftDeleteModel

User = get_user_model()


class WebhookEvent(models.TextChoices):
    """Webhook event type choices."""

    # Issue events
    ISSUE_CREATED = 'issue:created', _('Issue Created')
    ISSUE_UPDATED = 'issue:updated', _('Issue Updated')
    ISSUE_DELETED = 'issue:deleted', _('Issue Deleted')
    ISSUE_ASSIGNED = 'issue:assigned', _('Issue Assigned')
    ISSUE_TRANSITIONED = 'issue:transitioned', _('Issue Transitioned')
    ISSUE_COMMENTED = 'issue:commented', _('Issue Commented')

    # Sprint events
    SPRINT_STARTED = 'sprint:started', _('Sprint Started')
    SPRINT_COMPLETED = 'sprint:completed', _('Sprint Completed')
    SPRINT_UPDATED = 'sprint:updated', _('Sprint Updated')

    # Project events
    PROJECT_CREATED = 'project:created', _('Project Created')
    PROJECT_UPDATED = 'project:updated', _('Project Updated')
    PROJECT_DELETED = 'project:deleted', _('Project Deleted')

    # Automation events
    AUTOMATION_EXECUTED = 'automation:executed', _('Automation Executed')


class WebhookQuerySet(models.QuerySet):
    """Custom QuerySet for Webhook."""

    def active(self):
        """Filter active webhooks only."""
        return self.filter(is_active=True, deleted_at__isnull=True)

    def for_organization(self, organization):
        """Filter webhooks for an organization."""
        return self.filter(organization=organization)

    def for_project(self, project):
        """Filter webhooks for a project."""
        return self.filter(project=project)

    def for_event(self, event_type):
        """Filter webhooks subscribed to a specific event."""
        return self.filter(events__contains=[event_type])


class Webhook(TimestampedModel, SoftDeleteModel):
    """
    Webhook model for outgoing webhooks.

    Allows external systems to receive notifications about events.
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
        related_name='webhooks',
        help_text=_('Organization this webhook belongs to')
    )

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='webhooks',
        null=True,
        blank=True,
        help_text=_('Project this webhook applies to (null for organization-wide)')
    )

    name = models.CharField(
        max_length=200,
        verbose_name=_('name'),
        help_text=_('Webhook name')
    )

    description = models.TextField(
        blank=True,
        verbose_name=_('description'),
        help_text=_('Webhook description')
    )

    url = models.URLField(
        max_length=500,
        verbose_name=_('URL'),
        help_text=_('URL to send webhook requests to')
    )

    events = models.JSONField(
        default=list,
        verbose_name=_('events'),
        help_text=_('List of events to subscribe to')
    )

    secret = models.CharField(
        max_length=128,
        verbose_name=_('secret'),
        help_text=_('Secret key for HMAC signature generation')
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_('is active'),
        help_text=_('Whether this webhook is active')
    )

    # Headers to include in webhook requests
    custom_headers = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('custom headers'),
        help_text=_('Custom headers to include in webhook requests')
    )

    # Retry configuration
    max_retries = models.IntegerField(
        default=3,
        verbose_name=_('max retries'),
        help_text=_('Maximum number of retry attempts')
    )

    timeout_seconds = models.IntegerField(
        default=30,
        verbose_name=_('timeout seconds'),
        help_text=_('Request timeout in seconds')
    )

    # Statistics
    total_deliveries = models.IntegerField(
        default=0,
        verbose_name=_('total deliveries'),
        help_text=_('Total number of delivery attempts')
    )

    successful_deliveries = models.IntegerField(
        default=0,
        verbose_name=_('successful deliveries'),
        help_text=_('Number of successful deliveries')
    )

    failed_deliveries = models.IntegerField(
        default=0,
        verbose_name=_('failed deliveries'),
        help_text=_('Number of failed deliveries')
    )

    last_delivery_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('last delivery at'),
        help_text=_('When last delivery was attempted')
    )

    last_success_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('last success at'),
        help_text=_('When last successful delivery occurred')
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_webhooks',
        help_text=_('User who created this webhook')
    )

    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_webhooks',
        help_text=_('User who last updated this webhook')
    )

    objects = WebhookQuerySet.as_manager()

    class Meta:
        db_table = 'webhooks'
        verbose_name = _('webhook')
        verbose_name_plural = _('webhooks')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'is_active']),
            models.Index(fields=['project', 'is_active']),
            models.Index(fields=['is_active', '-created_at']),
        ]

    def __str__(self):
        return f"{self.name} ({self.url})"

    def save(self, *args, **kwargs):
        """Override save to generate secret if not set."""
        if not self.secret:
            self.secret = self.generate_secret()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_secret():
        """Generate a secure random secret."""
        return secrets.token_urlsafe(32)

    def is_subscribed_to(self, event_type: str) -> bool:
        """
        Check if webhook is subscribed to an event.

        Args:
            event_type: Event type to check

        Returns:
            True if subscribed, False otherwise
        """
        return event_type in self.events

    def increment_delivery_stats(self, success: bool):
        """
        Increment delivery statistics.

        Args:
            success: Whether delivery was successful
        """
        from django.utils import timezone

        self.total_deliveries += 1
        if success:
            self.successful_deliveries += 1
            self.last_success_at = timezone.now()
        else:
            self.failed_deliveries += 1

        self.last_delivery_at = timezone.now()
        self.save(update_fields=[
            'total_deliveries',
            'successful_deliveries',
            'failed_deliveries',
            'last_delivery_at',
            'last_success_at',
        ])

    def get_success_rate(self) -> float:
        """
        Calculate webhook success rate.

        Returns:
            Success rate as percentage (0-100)
        """
        if self.total_deliveries == 0:
            return 0.0
        return (self.successful_deliveries / self.total_deliveries) * 100

    def regenerate_secret(self):
        """Regenerate webhook secret."""
        self.secret = self.generate_secret()
        self.save(update_fields=['secret'])
        return self.secret
