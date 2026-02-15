"""
Django admin configuration for search app.
"""

from django.contrib import admin
from apps.search.models import SavedFilter, SearchHistory


@admin.register(SavedFilter)
class SavedFilterAdmin(admin.ModelAdmin):
    """Admin interface for SavedFilter model."""

    list_display = [
        'name', 'organization', 'project', 'is_shared',
        'is_favorite', 'usage_count', 'created_by', 'created_at'
    ]
    list_filter = ['is_shared', 'is_favorite', 'organization', 'created_at']
    search_fields = ['name', 'description', 'jql']
    readonly_fields = [
        'id', 'usage_count', 'last_used_at',
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
        ('Query', {
            'fields': (
                'jql',
            )
        }),
        ('Settings', {
            'fields': (
                'is_shared', 'is_favorite', 'config'
            )
        }),
        ('Statistics', {
            'fields': (
                'usage_count', 'last_used_at'
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


@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    """Admin interface for SearchHistory model."""

    list_display = [
        'user', 'organization', 'query_type',
        'results_count', 'execution_time_ms', 'created_at'
    ]
    list_filter = ['query_type', 'organization', 'created_at']
    search_fields = ['query', 'user__email']
    readonly_fields = [
        'id', 'organization', 'user', 'query', 'query_type',
        'results_count', 'execution_time_ms', 'created_at', 'updated_at'
    ]
    ordering = ['-created_at']

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id', 'organization', 'user'
            )
        }),
        ('Query', {
            'fields': (
                'query', 'query_type'
            )
        }),
        ('Results', {
            'fields': (
                'results_count', 'execution_time_ms'
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
            'organization', 'user'
        )

    def has_add_permission(self, request):
        """Disable adding search history via admin (created by system)."""
        return False

    def has_change_permission(self, request, obj=None):
        """Disable changing search history (audit trail)."""
        return False
