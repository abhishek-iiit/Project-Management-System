"""
Django admin configuration for organizations app.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from apps.organizations.models import Organization, OrganizationMember, OrganizationInvitation


class OrganizationMemberInline(admin.TabularInline):
    """Inline for organization members."""

    model = OrganizationMember
    extra = 0
    fields = ['user', 'role', 'is_active', 'invited_by', 'created_at']
    readonly_fields = ['created_at']
    autocomplete_fields = ['user', 'invited_by']


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    """Organization admin."""

    list_display = ['name', 'slug', 'is_active', 'member_count', 'created_by', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'slug', 'email']
    ordering = ['-created_at']
    inlines = [OrganizationMemberInline]

    fieldsets = (
        (None, {'fields': ('name', 'slug', 'description', 'logo', 'website')}),
        (_('Contact'), {'fields': ('email', 'phone')}),
        (_('Address'), {
            'fields': ('address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country'),
            'classes': ('collapse',)
        }),
        (_('Settings'), {'fields': ('settings', 'is_active')}),
        (_('Audit'), {'fields': ('created_by', 'updated_by', 'created_at', 'updated_at')}),
    )

    readonly_fields = ['created_by', 'updated_by', 'created_at', 'updated_at']
    autocomplete_fields = ['created_by', 'updated_by']

    def member_count(self, obj):
        """Display member count."""
        return obj.get_member_count()

    member_count.short_description = 'Members'


@admin.register(OrganizationMember)
class OrganizationMemberAdmin(admin.ModelAdmin):
    """Organization member admin."""

    list_display = ['user', 'organization', 'role', 'is_active', 'invited_by', 'created_at']
    list_filter = ['role', 'is_active', 'created_at']
    search_fields = ['user__email', 'user__username', 'organization__name']
    ordering = ['-created_at']

    fieldsets = (
        (None, {'fields': ('organization', 'user', 'role', 'is_active')}),
        (_('Invitation'), {'fields': ('invited_by', 'invitation_accepted_at')}),
        (_('Permissions'), {'fields': ('custom_permissions',)}),
        (_('Audit'), {'fields': ('created_by', 'updated_by', 'created_at', 'updated_at')}),
    )

    readonly_fields = ['created_by', 'updated_by', 'created_at', 'updated_at']
    autocomplete_fields = ['organization', 'user', 'invited_by', 'created_by', 'updated_by']


@admin.register(OrganizationInvitation)
class OrganizationInvitationAdmin(admin.ModelAdmin):
    """Organization invitation admin."""

    list_display = ['email', 'organization', 'role', 'status', 'invited_by', 'created_at', 'expires_at']
    list_filter = ['status', 'role', 'created_at', 'expires_at']
    search_fields = ['email', 'organization__name', 'invited_by__email']
    ordering = ['-created_at']

    fieldsets = (
        (None, {'fields': ('organization', 'email', 'role', 'status')}),
        (_('Invitation'), {'fields': ('invited_by', 'message', 'token')}),
        (_('Dates'), {'fields': ('expires_at', 'accepted_at', 'created_at', 'updated_at')}),
    )

    readonly_fields = ['token', 'accepted_at', 'created_at', 'updated_at']
    autocomplete_fields = ['organization', 'invited_by']
