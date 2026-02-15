"""
Django admin configuration for automation app.
"""

from django.contrib import admin
from django.utils.html import format_html
from apps.automation.models import AutomationRule, AutomationExecution


@admin.register(AutomationRule)
class AutomationRuleAdmin(admin.ModelAdmin):
    """Admin interface for AutomationRule model."""

    list_display = [
        'name', 'organization', 'project', 'trigger_type',
        'is_active', 'execution_count', 'last_executed_at', 'created_at'
    ]
    list_filter = ['trigger_type', 'is_active', 'organization']
    search_fields = ['name', 'description']
    readonly_fields = [
        'id', 'execution_count', 'last_executed_at',
        'created_at', 'updated_at', 'deleted_at'
    ]
    raw_id_fields = ['organization', 'project', 'created_by', 'updated_by']
    ordering = ['organization', 'name']

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id', 'organization', 'project', 'name', 'description'
            )
        }),
        ('Trigger', {
            'fields': (
                'trigger_type', 'trigger_config'
            )
        }),
        ('Conditions', {
            'fields': (
                'conditions',
            )
        }),
        ('Actions', {
            'fields': (
                'actions',
            )
        }),
        ('Status', {
            'fields': (
                'is_active',
            )
        }),
        ('Statistics', {
            'fields': (
                'execution_count', 'last_executed_at'
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


@admin.register(AutomationExecution)
class AutomationExecutionAdmin(admin.ModelAdmin):
    """Admin interface for AutomationExecution model."""

    list_display = [
        'rule_name', 'issue_key', 'status', 'conditions_passed',
        'execution_time_ms', 'created_at'
    ]
    list_filter = ['status', 'conditions_passed', 'created_at']
    search_fields = ['rule__name', 'issue__key', 'error_message']
    readonly_fields = [
        'id', 'rule', 'issue', 'trigger_event', 'status',
        'conditions_passed', 'conditions_result', 'actions_executed',
        'actions_result', 'error_message', 'error_details',
        'execution_time_ms', 'created_at', 'updated_at', 'deleted_at'
    ]
    ordering = ['-created_at']

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id', 'rule', 'issue'
            )
        }),
        ('Trigger', {
            'fields': (
                'trigger_event',
            )
        }),
        ('Execution', {
            'fields': (
                'status', 'execution_time_ms'
            )
        }),
        ('Conditions', {
            'fields': (
                'conditions_passed', 'conditions_result'
            ),
            'classes': ('collapse',)
        }),
        ('Actions', {
            'fields': (
                'actions_executed', 'actions_result'
            ),
            'classes': ('collapse',)
        }),
        ('Errors', {
            'fields': (
                'error_message', 'error_details'
            ),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': (
                'created_at', 'updated_at', 'deleted_at'
            ),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related(
            'rule', 'issue'
        )

    def rule_name(self, obj):
        """Display rule name."""
        return obj.rule.name
    rule_name.short_description = 'Rule'
    rule_name.admin_order_field = 'rule__name'

    def issue_key(self, obj):
        """Display issue key."""
        if obj.issue:
            return obj.issue.key
        return '-'
    issue_key.short_description = 'Issue'
    issue_key.admin_order_field = 'issue__key'

    def has_add_permission(self, request):
        """Disable adding executions via admin (created by system)."""
        return False

    def has_change_permission(self, request, obj=None):
        """Disable changing executions (audit trail)."""
        return False
