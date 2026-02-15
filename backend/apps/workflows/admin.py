"""
Django admin configuration for workflows app.
"""

from django.contrib import admin
from django.utils.html import format_html
from apps.workflows.models import Workflow, Status, Transition, WorkflowScheme


class StatusInline(admin.TabularInline):
    """Inline admin for statuses."""

    model = Status
    extra = 0
    raw_id_fields = ['created_by', 'updated_by']
    readonly_fields = ['created_at', 'updated_at', 'deleted_at']
    fields = [
        'name', 'category', 'is_initial', 'is_active',
        'position', 'created_at'
    ]
    ordering = ['position', 'name']

    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related('created_by')


class TransitionInline(admin.TabularInline):
    """Inline admin for transitions."""

    model = Transition
    extra = 0
    raw_id_fields = ['from_status', 'to_status', 'created_by', 'updated_by']
    readonly_fields = ['created_at', 'updated_at', 'deleted_at']
    fields = [
        'name', 'from_status', 'to_status', 'is_active',
        'position', 'created_at'
    ]
    ordering = ['position', 'name']

    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related(
            'from_status', 'to_status', 'created_by'
        )


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    """Admin interface for Workflow model."""

    list_display = [
        'name', 'organization', 'is_active', 'is_default',
        'statuses_count_display', 'transitions_count_display',
        'created_at'
    ]
    list_filter = [
        'is_active', 'is_default', 'created_at'
    ]
    search_fields = ['name', 'description']
    readonly_fields = [
        'id', 'statuses_count_display', 'transitions_count_display',
        'created_at', 'updated_at', 'deleted_at',
        'created_by', 'updated_by'
    ]
    raw_id_fields = ['organization', 'created_by', 'updated_by']
    inlines = [StatusInline, TransitionInline]

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id', 'organization', 'name', 'description'
            )
        }),
        ('Configuration', {
            'fields': (
                'is_active', 'is_default'
            )
        }),
        ('Statistics', {
            'fields': (
                'statuses_count_display',
                'transitions_count_display'
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
            'organization', 'created_by', 'updated_by'
        ).prefetch_related('statuses', 'transitions')

    def statuses_count_display(self, obj):
        """Display statuses count."""
        count = obj.statuses.filter(is_active=True).count()
        return format_html(
            '<span style="font-weight: bold;">{}</span>',
            count
        )
    statuses_count_display.short_description = 'Statuses'

    def transitions_count_display(self, obj):
        """Display transitions count."""
        count = obj.transitions.filter(is_active=True).count()
        return format_html(
            '<span style="font-weight: bold;">{}</span>',
            count
        )
    transitions_count_display.short_description = 'Transitions'


@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    """Admin interface for Status model."""

    list_display = [
        'name', 'workflow', 'category', 'is_initial',
        'is_active', 'position', 'created_at'
    ]
    list_filter = [
        'category', 'is_initial', 'is_active', 'created_at'
    ]
    search_fields = ['name', 'description', 'workflow__name']
    readonly_fields = [
        'id', 'outgoing_count', 'incoming_count',
        'created_at', 'updated_at', 'deleted_at',
        'created_by', 'updated_by'
    ]
    raw_id_fields = ['workflow', 'created_by', 'updated_by']

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id', 'workflow', 'name', 'description'
            )
        }),
        ('Configuration', {
            'fields': (
                'category', 'is_initial', 'is_active', 'position'
            )
        }),
        ('Transitions', {
            'fields': (
                'outgoing_count', 'incoming_count'
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
            'workflow', 'created_by', 'updated_by'
        )

    def outgoing_count(self, obj):
        """Display outgoing transitions count."""
        count = obj.outgoing_transitions.filter(is_active=True).count()
        return format_html(
            '<span style="font-weight: bold;">{}</span>',
            count
        )
    outgoing_count.short_description = 'Outgoing Transitions'

    def incoming_count(self, obj):
        """Display incoming transitions count."""
        count = obj.incoming_transitions.filter(is_active=True).count()
        return format_html(
            '<span style="font-weight: bold;">{}</span>',
            count
        )
    incoming_count.short_description = 'Incoming Transitions'


@admin.register(Transition)
class TransitionAdmin(admin.ModelAdmin):
    """Admin interface for Transition model."""

    list_display = [
        'name', 'workflow', 'from_status_name', 'to_status_name',
        'is_active', 'position', 'created_at'
    ]
    list_filter = [
        'is_active', 'created_at'
    ]
    search_fields = [
        'name', 'description',
        'workflow__name', 'from_status__name', 'to_status__name'
    ]
    readonly_fields = [
        'id', 'conditions_count', 'validators_count', 'post_functions_count',
        'created_at', 'updated_at', 'deleted_at',
        'created_by', 'updated_by'
    ]
    raw_id_fields = ['workflow', 'from_status', 'to_status', 'created_by', 'updated_by']

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id', 'workflow', 'name', 'description'
            )
        }),
        ('Transition Configuration', {
            'fields': (
                'from_status', 'to_status', 'is_active', 'position'
            )
        }),
        ('Conditions', {
            'fields': (
                'conditions', 'conditions_count'
            )
        }),
        ('Validators', {
            'fields': (
                'validators', 'validators_count'
            )
        }),
        ('Post-Functions', {
            'fields': (
                'post_functions', 'post_functions_count'
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
            'workflow', 'from_status', 'to_status', 'created_by', 'updated_by'
        )

    def from_status_name(self, obj):
        """Display from status name."""
        return obj.from_status.name if obj.from_status else 'Initial'
    from_status_name.short_description = 'From Status'

    def to_status_name(self, obj):
        """Display to status name."""
        return obj.to_status.name
    to_status_name.short_description = 'To Status'

    def conditions_count(self, obj):
        """Display conditions count."""
        count = len(obj.conditions) if obj.conditions else 0
        return format_html(
            '<span style="font-weight: bold;">{}</span>',
            count
        )
    conditions_count.short_description = 'Conditions Count'

    def validators_count(self, obj):
        """Display validators count."""
        count = len(obj.validators) if obj.validators else 0
        return format_html(
            '<span style="font-weight: bold;">{}</span>',
            count
        )
    validators_count.short_description = 'Validators Count'

    def post_functions_count(self, obj):
        """Display post-functions count."""
        count = len(obj.post_functions) if obj.post_functions else 0
        return format_html(
            '<span style="font-weight: bold;">{}</span>',
            count
        )
    post_functions_count.short_description = 'Post-Functions Count'


@admin.register(WorkflowScheme)
class WorkflowSchemeAdmin(admin.ModelAdmin):
    """Admin interface for WorkflowScheme model."""

    list_display = [
        'name', 'project', 'default_workflow',
        'mappings_count_display', 'is_active', 'created_at'
    ]
    list_filter = [
        'is_active', 'created_at'
    ]
    search_fields = ['name', 'description', 'project__name']
    readonly_fields = [
        'id', 'mappings_count_display',
        'created_at', 'updated_at', 'deleted_at',
        'created_by', 'updated_by'
    ]
    raw_id_fields = ['project', 'default_workflow', 'created_by', 'updated_by']

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id', 'project', 'name', 'description'
            )
        }),
        ('Workflow Configuration', {
            'fields': (
                'default_workflow', 'mappings', 'mappings_count_display'
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
            'project', 'default_workflow', 'created_by', 'updated_by'
        )

    def mappings_count_display(self, obj):
        """Display mappings count."""
        count = len(obj.mappings) if obj.mappings else 0
        return format_html(
            '<span style="font-weight: bold;">{}</span>',
            count
        )
    mappings_count_display.short_description = 'Issue Type Mappings'
