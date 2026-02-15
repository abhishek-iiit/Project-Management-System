"""
Webhook service for sending and managing webhooks.
"""

import json
import hmac
import hashlib
import logging
import time
from typing import Dict, Any, Optional
import requests
from django.utils import timezone

from apps.webhooks.models import Webhook, WebhookDelivery, DeliveryStatus

logger = logging.getLogger(__name__)


class WebhookService:
    """Service for sending webhooks and managing deliveries."""

    @staticmethod
    def send_webhook(
        webhook: Webhook,
        event_type: str,
        event_data: Dict[str, Any],
        event_id: Optional[str] = None,
        async_delivery: bool = True,
    ) -> Optional[WebhookDelivery]:
        """
        Send a webhook notification.

        Args:
            webhook: Webhook instance to send
            event_type: Event type
            event_data: Event data payload
            event_id: Optional event entity ID
            async_delivery: Whether to send asynchronously via Celery

        Returns:
            WebhookDelivery instance if sync, None if async
        """
        # Check if webhook is active and subscribed to event
        if not webhook.is_active:
            logger.info(f"Webhook {webhook.id} is inactive, skipping")
            return None

        if not webhook.is_subscribed_to(event_type):
            logger.info(f"Webhook {webhook.id} not subscribed to {event_type}, skipping")
            return None

        # Build payload
        payload = WebhookService._build_payload(webhook, event_type, event_data)

        # Create delivery record
        delivery = WebhookDelivery.objects.create(
            webhook=webhook,
            event_type=event_type,
            event_id=event_id,
            payload=payload,
            request_url=webhook.url,
            status=DeliveryStatus.PENDING,
        )

        # Send webhook
        if async_delivery:
            # Queue for async delivery
            WebhookService._queue_delivery(delivery)
            return None
        else:
            # Send synchronously
            return WebhookService._execute_delivery(delivery)

    @staticmethod
    def _build_payload(webhook: Webhook, event_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build webhook payload.

        Args:
            webhook: Webhook instance
            event_type: Event type
            event_data: Event data

        Returns:
            Webhook payload dict
        """
        return {
            'webhook_id': str(webhook.id),
            'event': event_type,
            'timestamp': timezone.now().isoformat(),
            'organization': {
                'id': str(webhook.organization.id),
                'name': webhook.organization.name,
            },
            'project': {
                'id': str(webhook.project.id),
                'key': webhook.project.key,
                'name': webhook.project.name,
            } if webhook.project else None,
            'data': event_data,
        }

    @staticmethod
    def _generate_signature(payload: str, secret: str) -> str:
        """
        Generate HMAC signature for webhook payload.

        Args:
            payload: JSON payload string
            secret: Webhook secret

        Returns:
            HMAC signature (hex)
        """
        return hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    @staticmethod
    def _execute_delivery(delivery: WebhookDelivery) -> WebhookDelivery:
        """
        Execute webhook delivery.

        Args:
            delivery: WebhookDelivery instance

        Returns:
            Updated WebhookDelivery instance
        """
        start_time = time.time()

        try:
            # Prepare payload
            payload_json = json.dumps(delivery.payload)

            # Generate signature
            signature = WebhookService._generate_signature(
                payload_json,
                delivery.webhook.secret
            )

            # Prepare headers
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'BugsTracker-Webhooks/1.0',
                'X-Webhook-ID': str(delivery.webhook.id),
                'X-Webhook-Event': delivery.event_type,
                'X-Webhook-Signature': signature,
                'X-Webhook-Delivery-ID': str(delivery.id),
            }

            # Add custom headers
            if delivery.webhook.custom_headers:
                headers.update(delivery.webhook.custom_headers)

            # Store request details
            delivery.request_headers = headers
            delivery.request_body = payload_json
            delivery.save()

            # Send request
            response = requests.post(
                delivery.request_url,
                data=payload_json,
                headers=headers,
                timeout=delivery.webhook.timeout_seconds,
            )

            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)

            # Check if successful (2xx status codes)
            if 200 <= response.status_code < 300:
                delivery.mark_success(
                    status_code=response.status_code,
                    response_headers=dict(response.headers),
                    response_body=response.text[:10000],  # Limit to 10KB
                    duration_ms=duration_ms,
                )
                logger.info(f"Webhook {delivery.id} delivered successfully")
            else:
                # Non-2xx status code
                error_message = f"HTTP {response.status_code}: {response.reason}"
                delivery.mark_failed(
                    error_message=error_message,
                    status_code=response.status_code,
                    response_body=response.text[:10000],
                    duration_ms=duration_ms,
                )
                logger.warning(f"Webhook {delivery.id} failed: {error_message}")

                # Schedule retry if possible
                if delivery.can_retry():
                    retry_delay = delivery.get_retry_delay()
                    delivery.schedule_retry(retry_delay)
                    WebhookService._queue_retry(delivery, retry_delay)

        except requests.exceptions.Timeout:
            duration_ms = int((time.time() - start_time) * 1000)
            error_message = f"Request timeout after {delivery.webhook.timeout_seconds}s"
            delivery.mark_failed(
                error_message=error_message,
                error_details={'type': 'timeout'},
                duration_ms=duration_ms,
            )
            logger.error(f"Webhook {delivery.id} timeout: {error_message}")

            # Schedule retry
            if delivery.can_retry():
                retry_delay = delivery.get_retry_delay()
                delivery.schedule_retry(retry_delay)
                WebhookService._queue_retry(delivery, retry_delay)

        except requests.exceptions.ConnectionError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_message = f"Connection error: {str(e)}"
            delivery.mark_failed(
                error_message=error_message,
                error_details={'type': 'connection_error', 'details': str(e)},
                duration_ms=duration_ms,
            )
            logger.error(f"Webhook {delivery.id} connection error: {error_message}")

            # Schedule retry
            if delivery.can_retry():
                retry_delay = delivery.get_retry_delay()
                delivery.schedule_retry(retry_delay)
                WebhookService._queue_retry(delivery, retry_delay)

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_message = f"Unexpected error: {str(e)}"
            delivery.mark_failed(
                error_message=error_message,
                error_details={'type': 'exception', 'details': str(e)},
                duration_ms=duration_ms,
            )
            logger.error(f"Webhook {delivery.id} error: {error_message}", exc_info=True)

        return delivery

    @staticmethod
    def _queue_delivery(delivery: WebhookDelivery):
        """
        Queue webhook delivery for async execution.

        Args:
            delivery: WebhookDelivery instance
        """
        try:
            from tasks.webhook_tasks import send_webhook_delivery
            send_webhook_delivery.delay(str(delivery.id))
            logger.info(f"Queued webhook delivery {delivery.id}")
        except ImportError:
            # Celery not configured, execute synchronously
            logger.warning("Celery not configured, executing webhook synchronously")
            WebhookService._execute_delivery(delivery)

    @staticmethod
    def _queue_retry(delivery: WebhookDelivery, delay_seconds: int):
        """
        Queue webhook retry.

        Args:
            delivery: WebhookDelivery instance
            delay_seconds: Delay before retry
        """
        try:
            from tasks.webhook_tasks import retry_webhook_delivery
            retry_webhook_delivery.apply_async(
                args=[str(delivery.id)],
                countdown=delay_seconds,
            )
            logger.info(f"Scheduled retry for delivery {delivery.id} in {delay_seconds}s")
        except ImportError:
            logger.warning("Celery not configured, cannot schedule retry")

    @staticmethod
    def test_webhook(webhook: Webhook) -> WebhookDelivery:
        """
        Send a test webhook delivery.

        Args:
            webhook: Webhook instance to test

        Returns:
            WebhookDelivery instance with test results
        """
        test_payload = {
            'test': True,
            'message': 'This is a test webhook delivery',
            'webhook_id': str(webhook.id),
            'timestamp': timezone.now().isoformat(),
        }

        delivery = WebhookDelivery.objects.create(
            webhook=webhook,
            event_type='webhook:test',
            payload=test_payload,
            request_url=webhook.url,
            status=DeliveryStatus.PENDING,
        )

        return WebhookService._execute_delivery(delivery)

    @staticmethod
    def broadcast_event(event_type: str, event_data: Dict[str, Any], organization, project=None):
        """
        Broadcast event to all subscribed webhooks.

        Args:
            event_type: Event type
            event_data: Event data
            organization: Organization instance
            project: Optional project instance
        """
        # Get relevant webhooks
        webhooks = Webhook.objects.active().for_organization(organization)

        if project:
            # Include project-specific and organization-wide webhooks
            webhooks = webhooks.filter(
                models.Q(project=project) | models.Q(project__isnull=True)
            )
        else:
            # Only organization-wide webhooks
            webhooks = webhooks.filter(project__isnull=True)

        # Filter by event subscription
        webhooks = webhooks.for_event(event_type)

        # Send to all webhooks
        for webhook in webhooks:
            WebhookService.send_webhook(
                webhook=webhook,
                event_type=event_type,
                event_data=event_data,
                event_id=event_data.get('id'),
            )

        logger.info(f"Broadcast {event_type} to {webhooks.count()} webhooks")


# Import models at the end to avoid circular imports
from django.db import models
