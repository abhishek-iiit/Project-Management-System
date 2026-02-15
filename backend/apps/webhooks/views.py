"""
Views for webhooks.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q

from apps.webhooks.models import Webhook, WebhookDelivery, DeliveryStatus
from apps.webhooks.serializers import (
    WebhookSerializer,
    WebhookCreateSerializer,
    WebhookDeliverySerializer,
    WebhookDeliveryListSerializer,
    WebhookStatsSerializer,
)
from apps.webhooks.services import WebhookService


class WebhookViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing webhooks.

    Endpoints:
        GET    /webhooks/                 - List webhooks
        POST   /webhooks/                 - Create webhook
        GET    /webhooks/{id}/            - Retrieve webhook
        PUT    /webhooks/{id}/            - Update webhook
        DELETE /webhooks/{id}/            - Delete webhook (soft delete)
        POST   /webhooks/{id}/test/       - Test webhook
        POST   /webhooks/{id}/regenerate-secret/ - Regenerate secret
        GET    /webhooks/{id}/deliveries/ - Get webhook deliveries
        GET    /webhooks/stats/           - Get webhook statistics
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get queryset filtered by organization."""
        user = self.request.user
        organization = getattr(user, 'current_organization', None)

        if not organization:
            return Webhook.objects.none()

        queryset = Webhook.objects.for_organization(organization).active()

        # Filter by project if provided
        project_id = self.request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(
                Q(project_id=project_id) | Q(project__isnull=True)
            )

        # Filter by active status
        if self.request.query_params.get('active') == 'true':
            queryset = queryset.filter(is_active=True)
        elif self.request.query_params.get('active') == 'false':
            queryset = queryset.filter(is_active=False)

        return queryset.select_related(
            'organization',
            'project',
            'created_by',
            'updated_by',
        )

    def get_serializer_class(self):
        """Get appropriate serializer class."""
        if self.action == 'create':
            return WebhookCreateSerializer
        return WebhookSerializer

    def perform_create(self, serializer):
        """Create webhook with current user."""
        user = self.request.user
        serializer.save(created_by=user, updated_by=user)

    def perform_update(self, serializer):
        """Update webhook with current user."""
        user = self.request.user
        serializer.save(updated_by=user)

    def destroy(self, request, *args, **kwargs):
        """Soft delete webhook."""
        webhook = self.get_object()
        from django.utils import timezone
        webhook.deleted_at = timezone.now()
        webhook.save()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """Test webhook by sending a test delivery."""
        webhook = self.get_object()

        delivery = WebhookService.test_webhook(webhook)

        serializer = WebhookDeliverySerializer(delivery)
        return Response({
            'message': 'Test webhook sent',
            'delivery': serializer.data,
        })

    @action(detail=True, methods=['post'], url_path='regenerate-secret')
    def regenerate_secret(self, request, pk=None):
        """Regenerate webhook secret."""
        webhook = self.get_object()
        new_secret = webhook.regenerate_secret()

        return Response({
            'message': 'Secret regenerated successfully',
            'secret': new_secret,
        })

    @action(detail=True, methods=['get'])
    def deliveries(self, request, pk=None):
        """Get deliveries for this webhook."""
        webhook = self.get_object()

        deliveries = WebhookDelivery.objects.for_webhook(webhook)

        # Filter by status
        delivery_status = request.query_params.get('status')
        if delivery_status:
            deliveries = deliveries.filter(status=delivery_status)

        # Order by most recent
        deliveries = deliveries.order_by('-created_at')

        # Paginate
        page = self.paginate_queryset(deliveries)
        if page is not None:
            serializer = WebhookDeliveryListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = WebhookDeliveryListSerializer(deliveries, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get webhook statistics."""
        user = request.user
        organization = getattr(user, 'current_organization', None)

        if not organization:
            return Response(
                {'error': 'No organization selected'},
                status=status.HTTP_400_BAD_REQUEST
            )

        webhooks = Webhook.objects.for_organization(organization).active()

        total_webhooks = webhooks.count()
        active_webhooks = webhooks.filter(is_active=True).count()

        # Aggregate delivery stats
        total_deliveries = sum(w.total_deliveries for w in webhooks)
        successful_deliveries = sum(w.successful_deliveries for w in webhooks)
        failed_deliveries = sum(w.failed_deliveries for w in webhooks)

        success_rate = 0.0
        if total_deliveries > 0:
            success_rate = (successful_deliveries / total_deliveries) * 100

        # Deliveries by status
        deliveries = WebhookDelivery.objects.filter(webhook__in=webhooks)
        deliveries_by_status = {}
        for item in deliveries.values('status').annotate(count=Count('id')):
            deliveries_by_status[item['status']] = item['count']

        # Deliveries by event type
        deliveries_by_event = {}
        for item in deliveries.values('event_type').annotate(count=Count('id')):
            deliveries_by_event[item['event_type']] = item['count']

        stats = {
            'total_webhooks': total_webhooks,
            'active_webhooks': active_webhooks,
            'total_deliveries': total_deliveries,
            'successful_deliveries': successful_deliveries,
            'failed_deliveries': failed_deliveries,
            'success_rate': round(success_rate, 2),
            'deliveries_by_status': deliveries_by_status,
            'deliveries_by_event': deliveries_by_event,
        }

        serializer = WebhookStatsSerializer(stats)
        return Response(serializer.data)


class WebhookDeliveryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for webhook deliveries (read-only).

    Endpoints:
        GET /webhook-deliveries/     - List deliveries
        GET /webhook-deliveries/{id}/ - Retrieve delivery
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get queryset filtered by organization."""
        user = self.request.user
        organization = getattr(user, 'current_organization', None)

        if not organization:
            return WebhookDelivery.objects.none()

        queryset = WebhookDelivery.objects.filter(
            webhook__organization=organization
        )

        # Filter by webhook
        webhook_id = self.request.query_params.get('webhook')
        if webhook_id:
            queryset = queryset.filter(webhook_id=webhook_id)

        # Filter by status
        delivery_status = self.request.query_params.get('status')
        if delivery_status:
            queryset = queryset.filter(status=delivery_status)

        # Filter by event type
        event_type = self.request.query_params.get('event_type')
        if event_type:
            queryset = queryset.filter(event_type=event_type)

        return queryset.select_related('webhook').order_by('-created_at')

    def get_serializer_class(self):
        """Get appropriate serializer class."""
        if self.action == 'list':
            return WebhookDeliveryListSerializer
        return WebhookDeliverySerializer
