"""
Django admin configuration for projects app.
"""

from django.contrib import admin
from django.utils.html import format_html
from apps.projects.models import Project, ProjectMember, ProjectRole, ProjectTemplate


class ProjectMemberInline(admin.TabularInline):
    """Inline admin for project members."""

    model = ProjectMember
    extra = 0
    raw_id_fields = ['user', 'role', 'created_by', 'updated_by']
    readonly_fields = ['created_at', 'updated_at', 'deleted_at']
    fields = [
        'user', 'role', 'is_admin', 'custom_permissions',
        'is_active', 'created_at'
    ]

    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related(
            'user', 'role', 'created_by'
        )


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """Admin interface for Project model."""

    list_display = [
        'key', 'name', 'organization', 'project_type',
        'lead', 'is_active', 'is_private',
        'members_count_display', 'created_at'
    ]
    list_filter = [
        'is_active', 'is_private', 'project_type',
        'template', 'created_at'
    ]
    search_fields = ['name', 'key', 'description']
    readonly_fields = [
        'id', 'members_count_display', 'issues_count_display',
        'created_at', 'updated_at', 'deleted_at',
        'created_by', 'updated_by'
    ]
    raw_id_fields = ['organization', 'lead', 'created_by', 'updated_by']
    inlines = [ProjectMemberInline]

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id', 'organization', 'name', 'key',
                'description', 'avatar'
            )
        }),
        ('Configuration', {
            'fields': (
                'lead', 'project_type', 'template',
                'settings'
            )
        }),
        ('Access Control', {
            'fields': (
                'is_active', 'is_private'
            )
        }),
        ('Statistics', {
            'fields': (
                'members_count_display',
                'issues_count_display'
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
            'organization', 'lead', 'created_by', 'updated_by'
        ).prefetch_related(
            'project_members', 'project_members__user'
        )

    def members_count_display(self, obj):
        """Display members count."""
        try:
            count = obj.get_member_count()
            return format_html(
                '<span style="font-weight: bold;">{}</span>',
                count
            )
        except Exception:
            return '-'
    members_count_display.short_description = 'Members'

    def issues_count_display(self, obj):
        """Display issues count."""
        try:
            count = obj.get_issue_count()
            return format_html(
                '<span style="font-weight: bold;">{}</span>',
                count
            )
        except Exception:
            return '-'
    issues_count_display.short_description = 'Issues'


@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    """Admin interface for ProjectMember model."""

    list_display = [
        'project', 'user', 'role', 'is_admin',
        'is_active', 'created_at'
    ]
    list_filter = [
        'is_admin', 'is_active', 'created_at'
    ]
    search_fields = [
        'project__name', 'project__key',
        'user__email', 'user__username'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'deleted_at',
        'created_by', 'updated_by'
    ]
    raw_id_fields = ['project', 'user', 'role', 'created_by', 'updated_by']

    fieldsets = (
        ('Membership', {
            'fields': (
                'id', 'project', 'user', 'role', 'is_admin'
            )
        }),
        ('Permissions', {
            'fields': (
                'custom_permissions',
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
            'project', 'user', 'role', 'created_by', 'updated_by'
        )


@admin.register(ProjectRole)
class ProjectRoleAdmin(admin.ModelAdmin):
    """Admin interface for ProjectRole model."""

    list_display = [
        'name', 'organization', 'is_default',
        'permissions_count', 'created_at'
    ]
    list_filter = [
        'is_default', 'created_at'
    ]
    search_fields = ['name', 'description']
    readonly_fields = [
        'id', 'permissions_count', 'created_at',
        'updated_at', 'deleted_at',
        'created_by', 'updated_by'
    ]
    raw_id_fields = ['organization', 'created_by', 'updated_by']

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id', 'organization', 'name', 'description'
            )
        }),
        ('Configuration', {
            'fields': (
                'is_default', 'permissions', 'permissions_count'
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

    def permissions_count(self, obj):
        """Display permissions count."""
        if isinstance(obj.permissions, dict):
            count = len(obj.permissions)
            return format_html(
                '<span style="font-weight: bold;">{}</span>',
                count
            )
        return 0
    permissions_count.short_description = 'Permissions Count'


@admin.register(ProjectTemplate)
class ProjectTemplateAdmin(admin.ModelAdmin):
    """Admin interface for ProjectTemplate model."""

    list_display = [
        'name', 'organization', 'template_type',
        'config_keys_count', 'created_at'
    ]
    list_filter = [
        'template_type', 'created_at'
    ]
    search_fields = ['name', 'description']
    readonly_fields = [
        'id', 'config_keys_count',
        'created_at', 'updated_at', 'deleted_at'
    ]
    raw_id_fields = ['organization']

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id', 'organization', 'name', 'description'
            )
        }),
        ('Template Configuration', {
            'fields': (
                'template_type', 'config', 'config_keys_count', 'is_default'
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at', 'deleted_at'
            ),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related('organization')

    def config_keys_count(self, obj):
        """Display config keys count."""
        if isinstance(obj.config, dict):
            count = len(obj.config.keys())
            return format_html(
                '<span style="font-weight: bold;">{}</span>',
                count
            )
        return 0
    config_keys_count.short_description = 'Config Keys'
