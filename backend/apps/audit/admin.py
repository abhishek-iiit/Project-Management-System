"""
Django admin configuration for audit app.
"""

from django.contrib import admin
from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin interface for AuditLog model."""

    list_display = [
        'created_at', 'user', 'action', 'entity_type', 'entity_name',
        'success', 'ip_address'
    ]
    list_filter = ['action', 'entity_type', 'success', 'created_at']
    search_fields = ['user__email', 'entity_type', 'entity_name', 'ip_address']
    readonly_fields = [
        'id', 'organization', 'user', 'action', 'entity_type', 'entity_id',
        'entity_name', 'changes', 'metadata', 'ip_address', 'user_agent',
        'request_method', 'request_path', 'success', 'error_message',
        'duration_ms', 'tags', 'created_at', 'updated_at'
    ]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id', 'organization', 'user', 'created_at'
            )
        }),
        ('Action', {
            'fields': (
                'action', 'entity_type', 'entity_id', 'entity_name', 'success'
            )
        }),
        ('Changes', {
            'fields': (
                'changes', 'metadata'
            ),
            'classes': ('collapse',)
        }),
        ('Request Information', {
            'fields': (
                'ip_address', 'user_agent', 'request_method', 'request_path'
            ),
            'classes': ('collapse',)
        }),
        ('Additional', {
            'fields': (
                'error_message', 'duration_ms', 'tags'
            ),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related(
            'organization', 'user'
        )

    def has_add_permission(self, request):
        """Disable adding logs via admin (created by system)."""
        return False

    def has_change_permission(self, request, obj=None):
        """Disable changing logs (immutable audit trail)."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete audit logs."""
        return request.user.is_superuser
