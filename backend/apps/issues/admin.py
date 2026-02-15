"""
Django admin configuration for issues app.
"""

from django.contrib import admin
from django.utils.html import format_html
from apps.issues.models import (
    Issue, IssueType, Priority, Label, Comment, Attachment,
    IssueLink, IssueLinkType, Watcher
)


@admin.register(IssueType)
class IssueTypeAdmin(admin.ModelAdmin):
    """Admin interface for IssueType model."""

    list_display = [
        'name', 'organization', 'is_subtask', 'is_epic',
        'is_default', 'is_active', 'position', 'created_at'
    ]
    list_filter = ['is_subtask', 'is_epic', 'is_default', 'is_active']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at', 'deleted_at']
    raw_id_fields = ['organization', 'created_by', 'updated_by']
    ordering = ['organization', 'position', 'name']


@admin.register(Priority)
class PriorityAdmin(admin.ModelAdmin):
    """Admin interface for Priority model."""

    list_display = [
        'name', 'organization', 'level', 'color_display',
        'is_default', 'is_active', 'created_at'
    ]
    list_filter = ['level', 'is_default', 'is_active']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at', 'deleted_at']
    raw_id_fields = ['organization', 'created_by', 'updated_by']
    ordering = ['organization', 'level', 'name']

    def color_display(self, obj):
        """Display color swatch."""
        if obj.color:
            return format_html(
                '<span style="background-color: {}; padding: 5px 15px; border-radius: 3px;">&nbsp;</span> {}',
                obj.color, obj.color
            )
        return '-'
    color_display.short_description = 'Color'


class CommentInline(admin.TabularInline):
    """Inline admin for comments."""

    model = Comment
    extra = 0
    raw_id_fields = ['user', 'created_by', 'updated_by']
    readonly_fields = ['created_at', 'updated_at']
    fields = ['user', 'body', 'created_at']
    ordering = ['created_at']


class AttachmentInline(admin.TabularInline):
    """Inline admin for attachments."""

    model = Attachment
    extra = 0
    raw_id_fields = ['created_by', 'updated_by']
    readonly_fields = ['filename', 'file_size', 'mime_type', 'created_at']
    fields = ['file', 'filename', 'file_size', 'created_at']
    ordering = ['-created_at']


class WatcherInline(admin.TabularInline):
    """Inline admin for watchers."""

    model = Watcher
    extra = 0
    raw_id_fields = ['user']
    readonly_fields = ['created_at']
    fields = ['user', 'created_at']


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    """Admin interface for Issue model."""

    list_display = [
        'key', 'summary_truncated', 'project', 'issue_type',
        'status', 'priority', 'assignee', 'created_at'
    ]
    list_filter = [
        'project', 'issue_type', 'status', 'priority',
        'created_at'
    ]
    search_fields = ['key', 'summary', 'description']
    readonly_fields = [
        'id', 'key', 'comments_count_display', 'attachments_count_display',
        'watchers_count_display', 'created_at', 'updated_at', 'deleted_at'
    ]
    raw_id_fields = [
        'project', 'issue_type', 'status', 'priority',
        'reporter', 'assignee', 'epic', 'parent',
        'created_by', 'updated_by'
    ]
    inlines = [CommentInline, AttachmentInline, WatcherInline]

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id', 'key', 'project', 'issue_type',
                'summary', 'description'
            )
        }),
        ('Workflow', {
            'fields': (
                'status', 'priority', 'resolution', 'resolution_date'
            )
        }),
        ('Assignment', {
            'fields': (
                'reporter', 'assignee'
            )
        }),
        ('Hierarchy', {
            'fields': (
                'epic', 'parent'
            )
        }),
        ('Time Tracking', {
            'fields': (
                'original_estimate', 'remaining_estimate', 'time_spent',
                'due_date'
            )
        }),
        ('Custom Fields', {
            'fields': (
                'custom_field_values',
            ),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': (
                'comments_count_display',
                'attachments_count_display',
                'watchers_count_display'
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
            'project', 'issue_type', 'status', 'priority',
            'reporter', 'assignee', 'epic', 'parent',
            'created_by', 'updated_by'
        )

    def summary_truncated(self, obj):
        """Display truncated summary."""
        if len(obj.summary) > 50:
            return obj.summary[:50] + '...'
        return obj.summary
    summary_truncated.short_description = 'Summary'

    def comments_count_display(self, obj):
        """Display comments count."""
        count = obj.comments.count()
        return format_html('<span style="font-weight: bold;">{}</span>', count)
    comments_count_display.short_description = 'Comments'

    def attachments_count_display(self, obj):
        """Display attachments count."""
        count = obj.attachments.count()
        return format_html('<span style="font-weight: bold;">{}</span>', count)
    attachments_count_display.short_description = 'Attachments'

    def watchers_count_display(self, obj):
        """Display watchers count."""
        count = obj.watchers.count()
        return format_html('<span style="font-weight: bold;">{}</span>', count)
    watchers_count_display.short_description = 'Watchers'


@admin.register(Label)
class LabelAdmin(admin.ModelAdmin):
    """Admin interface for Label model."""

    list_display = ['name', 'organization', 'project', 'color_display', 'created_at']
    list_filter = ['organization', 'project']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'deleted_at']
    raw_id_fields = ['project', 'organization']

    def color_display(self, obj):
        """Display color swatch."""
        if obj.color:
            return format_html(
                '<span style="background-color: {}; padding: 5px 15px; border-radius: 3px;">&nbsp;</span> {}',
                obj.color, obj.color
            )
        return '-'
    color_display.short_description = 'Color'


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """Admin interface for Comment model."""

    list_display = ['issue', 'user', 'body_truncated', 'created_at']
    list_filter = ['created_at']
    search_fields = ['body', 'issue__key']
    readonly_fields = ['id', 'created_at', 'updated_at', 'deleted_at']
    raw_id_fields = ['issue', 'user', 'created_by', 'updated_by']
    ordering = ['-created_at']

    def body_truncated(self, obj):
        """Display truncated body."""
        if len(obj.body) > 100:
            return obj.body[:100] + '...'
        return obj.body
    body_truncated.short_description = 'Comment'


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    """Admin interface for Attachment model."""

    list_display = [
        'filename', 'issue', 'file_size_display',
        'mime_type', 'created_at'
    ]
    list_filter = ['mime_type', 'created_at']
    search_fields = ['filename', 'issue__key']
    readonly_fields = [
        'id', 'filename', 'file_size', 'mime_type',
        'created_at', 'updated_at', 'deleted_at'
    ]
    raw_id_fields = ['issue', 'created_by', 'updated_by']
    ordering = ['-created_at']

    def file_size_display(self, obj):
        """Display file size in human-readable format."""
        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    file_size_display.short_description = 'Size'


@admin.register(IssueLinkType)
class IssueLinkTypeAdmin(admin.ModelAdmin):
    """Admin interface for IssueLinkType model."""

    list_display = [
        'name', 'organization', 'outward_description',
        'inward_description', 'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'deleted_at']
    raw_id_fields = ['organization']


@admin.register(IssueLink)
class IssueLinkAdmin(admin.ModelAdmin):
    """Admin interface for IssueLink model."""

    list_display = [
        'from_issue', 'link_type', 'to_issue', 'created_at'
    ]
    list_filter = ['link_type', 'created_at']
    search_fields = ['from_issue__key', 'to_issue__key']
    readonly_fields = ['id', 'created_at', 'updated_at', 'deleted_at']
    raw_id_fields = ['from_issue', 'to_issue', 'link_type', 'created_by', 'updated_by']
    ordering = ['-created_at']


@admin.register(Watcher)
class WatcherAdmin(admin.ModelAdmin):
    """Admin interface for Watcher model."""

    list_display = ['user', 'issue', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__email', 'issue__key']
    readonly_fields = ['id', 'created_at', 'updated_at', 'deleted_at']
    raw_id_fields = ['issue', 'user']
    ordering = ['-created_at']
