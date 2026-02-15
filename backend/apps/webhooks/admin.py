"""
Django admin configuration for webhooks app.
"""

from django.contrib import admin
from apps.webhooks.models import Webhook, WebhookDelivery


@admin.register(Webhook)
class WebhookAdmin(admin.ModelAdmin):
    """Admin interface for Webhook model."""

    list_display = [
        'name', 'url', 'organization', 'project', 'is_active',
        'total_deliveries', 'successful_deliveries', 'failed_deliveries',
        'last_delivery_at', 'created_at'
    ]
    list_filter = ['is_active', 'organization', 'created_at']
    search_fields = ['name', 'url', 'description']
    readonly_fields = [
        'id', 'secret', 'total_deliveries', 'successful_deliveries',
        'failed_deliveries', 'last_delivery_at', 'last_success_at',
        'created_at', 'updated_at', 'deleted_at'
    ]
    raw_id_fields = ['organization', 'project', 'created_by', 'updated_by']
    ordering = ['-created_at']

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id', 'organization', 'project', 'name', 'description'
            )
        }),
        ('Configuration', {
            'fields': (
                'url', 'events', 'secret', 'is_active'
            )
        }),
        ('Advanced Settings', {
            'fields': (
                'custom_headers', 'max_retries', 'timeout_seconds'
            ),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': (
                'total_deliveries', 'successful_deliveries', 'failed_deliveries',
                'last_delivery_at', 'last_success_at'
            ),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': (
                'created_by', 'created_at',
                'updated_by', 'updated_at',
                'deleted_at'
            ),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related(
            'organization', 'project', 'created_by', 'updated_by'
        )


@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(admin.ModelAdmin):
    """Admin interface for WebhookDelivery model."""

    list_display = [
        'webhook', 'event_type', 'status', 'response_status_code',
        'duration_ms', 'retry_count', 'created_at', 'delivered_at'
    ]
    list_filter = ['status', 'event_type', 'created_at']
    search_fields = ['webhook__name', 'event_type', 'error_message']
    readonly_fields = [
        'id', 'webhook', 'event_type', 'event_id', 'payload', 'status',
        'request_url', 'request_headers', 'request_body',
        'response_status_code', 'response_headers', 'response_body',
        'error_message', 'error_details', 'duration_ms', 'delivered_at',
        'retry_count', 'next_retry_at', 'created_at', 'updated_at'
    ]
    ordering = ['-created_at']

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id', 'webhook', 'event_type', 'event_id', 'status'
            )
        }),
        ('Request', {
            'fields': (
                'request_url', 'request_headers', 'request_body'
            ),
            'classes': ('collapse',)
        }),
        ('Response', {
            'fields': (
                'response_status_code', 'response_headers', 'response_body'
            ),
            'classes': ('collapse',)
        }),
        ('Error Details', {
            'fields': (
                'error_message', 'error_details'
            ),
            'classes': ('collapse',)
        }),
        ('Timing & Retry', {
            'fields': (
                'duration_ms', 'delivered_at', 'retry_count', 'next_retry_at'
            )
        }),
        ('Payload', {
            'fields': (
                'payload',
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related('webhook')

    def has_add_permission(self, request):
        """Disable adding deliveries via admin (created by system)."""
        return False

    def has_change_permission(self, request, obj=None):
        """Disable changing deliveries (audit trail)."""
        return False
