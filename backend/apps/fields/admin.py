"""
Django admin configuration for fields app.
"""

from django.contrib import admin
from django.utils.html import format_html
from apps.fields.models import FieldDefinition, FieldContext, FieldScheme


@admin.register(FieldDefinition)
class FieldDefinitionAdmin(admin.ModelAdmin):
    """Admin interface for FieldDefinition model."""

    list_display = [
        'name', 'organization', 'field_type', 'is_required',
        'is_active', 'position', 'created_at'
    ]
    list_filter = ['field_type', 'is_required', 'is_active', 'organization']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at', 'deleted_at']
    raw_id_fields = ['organization', 'created_by', 'updated_by']
    ordering = ['organization', 'position', 'name']

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id', 'organization', 'name', 'description', 'field_type'
            )
        }),
        ('Configuration', {
            'fields': (
                'config', 'default_value', 'is_required'
            )
        }),
        ('UI Settings', {
            'fields': (
                'placeholder', 'help_text', 'position'
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
            'organization', 'created_by', 'updated_by'
        )


@admin.register(FieldContext)
class FieldContextAdmin(admin.ModelAdmin):
    """Admin interface for FieldContext model."""

    list_display = [
        'field', 'project', 'issue_type', 'is_required',
        'is_visible', 'position', 'created_at'
    ]
    list_filter = ['is_visible', 'field__field_type']
    search_fields = ['field__name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'deleted_at']
    raw_id_fields = ['field', 'project', 'issue_type', 'created_by', 'updated_by']
    ordering = ['field', 'project', 'issue_type', 'position']

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id', 'field'
            )
        }),
        ('Scope', {
            'fields': (
                'project', 'issue_type'
            )
        }),
        ('Configuration', {
            'fields': (
                'is_required', 'is_visible', 'position'
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
            'field', 'project', 'issue_type',
            'created_by', 'updated_by'
        )


@admin.register(FieldScheme)
class FieldSchemeAdmin(admin.ModelAdmin):
    """Admin interface for FieldScheme model."""

    list_display = [
        'name', 'project', 'is_active', 'created_at'
    ]
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at', 'deleted_at']
    raw_id_fields = ['project', 'created_by', 'updated_by']
    ordering = ['project__name']

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id', 'project', 'name', 'description'
            )
        }),
        ('Configuration', {
            'fields': (
                'field_configs', 'is_active'
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
