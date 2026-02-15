"""
Django admin configuration for boards app.
"""

from django.contrib import admin
from django.utils.html import format_html
from apps.boards.models import Board, BoardIssue, Sprint


@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    """Admin interface for Board model."""

    list_display = [
        'name', 'project', 'board_type', 'is_active',
        'total_issues', 'created_at'
    ]
    list_filter = ['board_type', 'is_active', 'project']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at', 'deleted_at']
    raw_id_fields = ['project', 'created_by', 'updated_by']
    ordering = ['project', 'name']

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id', 'project', 'name', 'description', 'board_type'
            )
        }),
        ('Configuration', {
            'fields': (
                'column_config', 'swimlane_config', 'quick_filters',
                'filter_query', 'estimation_field'
            )
        }),
        ('Status', {
            'fields': (
                'is_active',
            )
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
            'project', 'created_by', 'updated_by'
        )

    def total_issues(self, obj):
        """Display total issues on board."""
        count = obj.board_issues.count()
        return format_html('<span style="font-weight: bold;">{}</span>', count)
    total_issues.short_description = 'Total Issues'


@admin.register(BoardIssue)
class BoardIssueAdmin(admin.ModelAdmin):
    """Admin interface for BoardIssue model."""

    list_display = [
        'issue_key', 'board', 'rank', 'created_at'
    ]
    list_filter = ['board']
    search_fields = ['issue__key', 'issue__summary']
    readonly_fields = ['id', 'created_at', 'updated_at', 'deleted_at']
    raw_id_fields = ['board', 'issue']
    ordering = ['board', 'rank']

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id', 'board', 'issue', 'rank'
            )
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
            'board', 'issue'
        )

    def issue_key(self, obj):
        """Display issue key."""
        return obj.issue.key
    issue_key.short_description = 'Issue'
    issue_key.admin_order_field = 'issue__key'


@admin.register(Sprint)
class SprintAdmin(admin.ModelAdmin):
    """Admin interface for Sprint model."""

    list_display = [
        'name', 'board', 'state', 'start_date', 'end_date',
        'total_issues', 'created_at'
    ]
    list_filter = ['state', 'board']
    search_fields = ['name', 'goal']
    readonly_fields = ['id', 'completed_date', 'created_at', 'updated_at', 'deleted_at']
    raw_id_fields = ['board', 'created_by', 'updated_by']
    filter_horizontal = ['issues']
    ordering = ['board', '-start_date']

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id', 'board', 'name', 'goal'
            )
        }),
        ('Dates', {
            'fields': (
                'start_date', 'end_date', 'completed_date'
            )
        }),
        ('State', {
            'fields': (
                'state',
            )
        }),
        ('Issues', {
            'fields': (
                'issues',
            )
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
            'board', 'created_by', 'updated_by'
        )

    def total_issues(self, obj):
        """Display total issues in sprint."""
        count = obj.issues.count()
        return format_html('<span style="font-weight: bold;">{}</span>', count)
    total_issues.short_description = 'Total Issues'
