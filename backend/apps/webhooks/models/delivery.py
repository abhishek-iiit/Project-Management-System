"""
Webhook delivery model for tracking webhook deliveries.
"""

import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimestampedModel


class DeliveryStatus(models.TextChoices):
    """Delivery status choices."""

    PENDING = 'pending', _('Pending')
    SUCCESS = 'success', _('Success')
    FAILED = 'failed', _('Failed')
    RETRYING = 'retrying', _('Retrying')


class WebhookDeliveryQuerySet(models.QuerySet):
    """Custom QuerySet for WebhookDelivery."""

    def for_webhook(self, webhook):
        """Filter deliveries for a specific webhook."""
        return self.filter(webhook=webhook)

    def successful(self):
        """Filter successful deliveries only."""
        return self.filter(status=DeliveryStatus.SUCCESS)

    def failed(self):
        """Filter failed deliveries only."""
        return self.filter(status=DeliveryStatus.FAILED)

    def pending(self):
        """Filter pending deliveries only."""
        return self.filter(status=DeliveryStatus.PENDING)

    def recent(self, limit=50):
        """Get recent deliveries."""
        return self.order_by('-created_at')[:limit]


class WebhookDelivery(TimestampedModel):
    """
    Webhook delivery model.

    Tracks individual webhook delivery attempts for audit trail.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text=_('Unique identifier (UUID4)')
    )

    webhook = models.ForeignKey(
        'webhooks.Webhook',
        on_delete=models.CASCADE,
        related_name='deliveries',
        help_text=_('Webhook that was delivered')
    )

    event_type = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name=_('event type'),
        help_text=_('Type of event that triggered this delivery')
    )

    event_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name=_('event ID'),
        help_text=_('ID of the entity that triggered the event')
    )

    payload = models.JSONField(
        verbose_name=_('payload'),
        help_text=_('JSON payload sent to webhook')
    )

    status = models.CharField(
        max_length=20,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PENDING,
        db_index=True,
        verbose_name=_('status'),
        help_text=_('Delivery status')
    )

    # Request details
    request_url = models.URLField(
        max_length=500,
        verbose_name=_('request URL'),
        help_text=_('URL the request was sent to')
    )

    request_headers = models.JSONField(
        default=dict,
        verbose_name=_('request headers'),
        help_text=_('Headers sent with the request')
    )

    request_body = models.TextField(
        verbose_name=_('request body'),
        help_text=_('Request body (JSON string)')
    )

    # Response details
    response_status_code = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('response status code'),
        help_text=_('HTTP status code from response')
    )

    response_headers = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('response headers'),
        help_text=_('Headers from response')
    )

    response_body = models.TextField(
        blank=True,
        verbose_name=_('response body'),
        help_text=_('Response body')
    )

    # Error details
    error_message = models.TextField(
        blank=True,
        verbose_name=_('error message'),
        help_text=_('Error message if delivery failed')
    )

    error_details = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('error details'),
        help_text=_('Detailed error information')
    )

    # Timing
    duration_ms = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('duration (ms)'),
        help_text=_('Request duration in milliseconds')
    )

    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('delivered at'),
        help_text=_('When the delivery was completed')
    )

    # Retry tracking
    retry_count = models.IntegerField(
        default=0,
        verbose_name=_('retry count'),
        help_text=_('Number of retry attempts')
    )

    next_retry_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('next retry at'),
        help_text=_('When to retry next (if applicable)')
    )

    objects = WebhookDeliveryQuerySet.as_manager()

    class Meta:
        db_table = 'webhook_deliveries'
        verbose_name = _('webhook delivery')
        verbose_name_plural = _('webhook deliveries')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['webhook', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['event_type', '-created_at']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.webhook.name} - {self.event_type} ({self.status})"

    def mark_success(self, status_code: int, response_headers: dict, response_body: str, duration_ms: int):
        """
        Mark delivery as successful.

        Args:
            status_code: HTTP status code
            response_headers: Response headers
            response_body: Response body
            duration_ms: Request duration in milliseconds
        """
        from django.utils import timezone

        self.status = DeliveryStatus.SUCCESS
        self.response_status_code = status_code
        self.response_headers = response_headers
        self.response_body = response_body
        self.duration_ms = duration_ms
        self.delivered_at = timezone.now()
        self.save()

        # Update webhook stats
        self.webhook.increment_delivery_stats(success=True)

    def mark_failed(self, error_message: str, error_details: dict = None, status_code: int = None,
                    response_body: str = '', duration_ms: int = None):
        """
        Mark delivery as failed.

        Args:
            error_message: Error message
            error_details: Optional detailed error information
            status_code: Optional HTTP status code
            response_body: Optional response body
            duration_ms: Optional request duration
        """
        from django.utils import timezone

        self.status = DeliveryStatus.FAILED
        self.error_message = error_message
        self.error_details = error_details or {}
        self.response_status_code = status_code
        self.response_body = response_body
        self.duration_ms = duration_ms
        self.delivered_at = timezone.now()
        self.save()

        # Update webhook stats
        self.webhook.increment_delivery_stats(success=False)

    def schedule_retry(self, retry_delay_seconds: int):
        """
        Schedule a retry for this delivery.

        Args:
            retry_delay_seconds: Delay in seconds before retry
        """
        from django.utils import timezone
        from datetime import timedelta

        self.status = DeliveryStatus.RETRYING
        self.retry_count += 1
        self.next_retry_at = timezone.now() + timedelta(seconds=retry_delay_seconds)
        self.save()

    def can_retry(self) -> bool:
        """
        Check if delivery can be retried.

        Returns:
            True if retry is possible, False otherwise
        """
        return (
            self.status in [DeliveryStatus.FAILED, DeliveryStatus.RETRYING] and
            self.retry_count < self.webhook.max_retries
        )

    def get_retry_delay(self) -> int:
        """
        Calculate retry delay using exponential backoff.

        Returns:
            Delay in seconds
        """
        # Exponential backoff: 60s, 120s, 240s, etc.
        base_delay = 60
        return base_delay * (2 ** self.retry_count)
