"""
Celery tasks for webhooks.
"""

from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_webhook_delivery(delivery_id: str):
    """
    Send webhook delivery asynchronously.

    Args:
        delivery_id: WebhookDelivery ID to send
    """
    from apps.webhooks.models import WebhookDelivery
    from apps.webhooks.services import WebhookService

    try:
        delivery = WebhookDelivery.objects.get(id=delivery_id)
        WebhookService._execute_delivery(delivery)
        logger.info(f"Webhook delivery {delivery_id} executed")
    except WebhookDelivery.DoesNotExist:
        logger.error(f"WebhookDelivery {delivery_id} not found")
    except Exception as e:
        logger.error(f"Failed to send webhook delivery {delivery_id}: {str(e)}")


@shared_task
def retry_webhook_delivery(delivery_id: str):
    """
    Retry a failed webhook delivery.

    Args:
        delivery_id: WebhookDelivery ID to retry
    """
    from apps.webhooks.models import WebhookDelivery, DeliveryStatus
    from apps.webhooks.services import WebhookService

    try:
        delivery = WebhookDelivery.objects.get(id=delivery_id)

        # Check if can still retry
        if not delivery.can_retry():
            logger.warning(f"Delivery {delivery_id} cannot be retried")
            return

        # Update status
        delivery.status = DeliveryStatus.RETRYING
        delivery.save()

        # Execute delivery
        WebhookService._execute_delivery(delivery)
        logger.info(f"Webhook delivery {delivery_id} retried")

    except WebhookDelivery.DoesNotExist:
        logger.error(f"WebhookDelivery {delivery_id} not found")
    except Exception as e:
        logger.error(f"Failed to retry webhook delivery {delivery_id}: {str(e)}")


@shared_task
def cleanup_old_deliveries(days=30):
    """
    Clean up old webhook deliveries.

    Args:
        days: Number of days to keep deliveries
    """
    from apps.webhooks.models import WebhookDelivery, DeliveryStatus
    from django.utils import timezone
    from datetime import timedelta

    cutoff_date = timezone.now() - timedelta(days=days)

    # Delete old successful deliveries
    deleted_count = WebhookDelivery.objects.filter(
        status=DeliveryStatus.SUCCESS,
        created_at__lt=cutoff_date,
    ).delete()[0]

    logger.info(f"Cleaned up {deleted_count} old webhook deliveries")
    return deleted_count


@shared_task
def process_failed_deliveries():
    """
    Process failed deliveries that are ready for retry.

    Runs periodically to check for deliveries that need to be retried.
    """
    from apps.webhooks.models import WebhookDelivery, DeliveryStatus
    from django.utils import timezone

    # Get failed deliveries ready for retry
    now = timezone.now()
    deliveries = WebhookDelivery.objects.filter(
        status=DeliveryStatus.RETRYING,
        next_retry_at__lte=now,
    )

    count = 0
    for delivery in deliveries:
        if delivery.can_retry():
            retry_webhook_delivery.delay(str(delivery.id))
            count += 1

    logger.info(f"Queued {count} webhook deliveries for retry")
    return count
