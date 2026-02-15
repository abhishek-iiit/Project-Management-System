"""
Serializers for webhooks.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model

from apps.webhooks.models import Webhook, WebhookDelivery, WebhookEvent

User = get_user_model()


class WebhookSerializer(serializers.ModelSerializer):
    """Serializer for Webhook model."""

    organization_name = serializers.CharField(source='organization.name', read_only=True)
    project_key = serializers.CharField(source='project.key', read_only=True, allow_null=True)
    project_name = serializers.CharField(source='project.name', read_only=True, allow_null=True)
    success_rate = serializers.SerializerMethodField()
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True, allow_null=True)

    class Meta:
        model = Webhook
        fields = [
            'id',
            'organization',
            'organization_name',
            'project',
            'project_key',
            'project_name',
            'name',
            'description',
            'url',
            'events',
            'secret',
            'is_active',
            'custom_headers',
            'max_retries',
            'timeout_seconds',
            'total_deliveries',
            'successful_deliveries',
            'failed_deliveries',
            'success_rate',
            'last_delivery_at',
            'last_success_at',
            'created_by',
            'created_by_email',
            'updated_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'secret',
            'total_deliveries',
            'successful_deliveries',
            'failed_deliveries',
            'last_delivery_at',
            'last_success_at',
            'created_by',
            'updated_by',
            'created_at',
            'updated_at',
        ]

    def get_success_rate(self, obj):
        """Get webhook success rate."""
        return round(obj.get_success_rate(), 2)


class WebhookCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating webhooks."""

    class Meta:
        model = Webhook
        fields = [
            'organization',
            'project',
            'name',
            'description',
            'url',
            'events',
            'is_active',
            'custom_headers',
            'max_retries',
            'timeout_seconds',
        ]

    def validate_events(self, value):
        """Validate event types."""
        valid_events = [e.value for e in WebhookEvent]
        for event in value:
            if event not in valid_events:
                raise serializers.ValidationError(f"Invalid event type: {event}")
        return value


class WebhookDeliverySerializer(serializers.ModelSerializer):
    """Serializer for WebhookDelivery model."""

    webhook_name = serializers.CharField(source='webhook.name', read_only=True)
    webhook_url = serializers.URLField(source='webhook.url', read_only=True)

    class Meta:
        model = WebhookDelivery
        fields = [
            'id',
            'webhook',
            'webhook_name',
            'webhook_url',
            'event_type',
            'event_id',
            'payload',
            'status',
            'request_url',
            'request_headers',
            'request_body',
            'response_status_code',
            'response_headers',
            'response_body',
            'error_message',
            'error_details',
            'duration_ms',
            'delivered_at',
            'retry_count',
            'next_retry_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class WebhookDeliveryListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing webhook deliveries."""

    webhook_name = serializers.CharField(source='webhook.name', read_only=True)

    class Meta:
        model = WebhookDelivery
        fields = [
            'id',
            'webhook',
            'webhook_name',
            'event_type',
            'status',
            'response_status_code',
            'duration_ms',
            'retry_count',
            'created_at',
            'delivered_at',
        ]


class WebhookStatsSerializer(serializers.Serializer):
    """Serializer for webhook statistics."""

    total_webhooks = serializers.IntegerField()
    active_webhooks = serializers.IntegerField()
    total_deliveries = serializers.IntegerField()
    successful_deliveries = serializers.IntegerField()
    failed_deliveries = serializers.IntegerField()
    success_rate = serializers.FloatField()
    deliveries_by_status = serializers.DictField()
    deliveries_by_event = serializers.DictField()
