"""
Django admin configuration for notifications app.
"""

from django.contrib import admin
from apps.notifications.models import Notification, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin interface for Notification model."""

    list_display = [
        'title', 'recipient', 'notification_type', 'is_read',
        'email_sent', 'created_at'
    ]
    list_filter = ['notification_type', 'read_at', 'email_sent', 'created_at']
    search_fields = ['title', 'message', 'recipient__email']
    readonly_fields = [
        'id', 'read_at', 'email_sent', 'email_sent_at', 'created_at', 'updated_at'
    ]
    raw_id_fields = ['organization', 'recipient', 'actor', 'issue', 'project', 'sprint']
    ordering = ['-created_at']

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id', 'organization', 'recipient', 'actor'
            )
        }),
        ('Notification', {
            'fields': (
                'notification_type', 'title', 'message', 'action_url', 'data'
            )
        }),
        ('Related Entities', {
            'fields': (
                'issue', 'project', 'sprint'
            )
        }),
        ('Status', {
            'fields': (
                'read_at', 'email_sent', 'email_sent_at'
            )
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
        return super().get_queryset(request).select_related(
            'organization', 'recipient', 'actor', 'issue', 'project', 'sprint'
        )


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    """Admin interface for NotificationPreference model."""

    list_display = [
        'user', 'organization', 'project', 'is_enabled',
        'in_app_enabled', 'email_enabled', 'push_enabled'
    ]
    list_filter = ['is_enabled', 'in_app_enabled', 'email_enabled', 'push_enabled', 'organization']
    search_fields = ['user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['organization', 'user', 'project']
    ordering = ['user', 'organization']

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id', 'organization', 'user', 'project'
            )
        }),
        ('Global Settings', {
            'fields': (
                'is_enabled', 'dnd_enabled', 'dnd_until'
            )
        }),
        ('Channel Settings', {
            'fields': (
                'in_app_enabled', 'email_enabled', 'push_enabled'
            )
        }),
        ('Email Settings', {
            'fields': (
                'email_digest_enabled', 'email_digest_frequency'
            )
        }),
        ('Event Preferences', {
            'fields': (
                'event_preferences', 'notify_on_mention', 'notify_on_watched_issue_update'
            )
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
        return super().get_queryset(request).select_related(
            'organization', 'user', 'project'
        )
