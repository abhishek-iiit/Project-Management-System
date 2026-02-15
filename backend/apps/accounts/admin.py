"""
Django admin configuration for accounts app.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import User, APIKey


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User admin."""

    list_display = ['email', 'username', 'full_name', 'is_active', 'is_staff', 'email_verified', 'created_at']
    list_filter = ['is_active', 'is_staff', 'is_superuser', 'email_verified', 'created_at']
    search_fields = ['email', 'username', 'first_name', 'last_name']
    ordering = ['-created_at']

    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'bio', 'avatar', 'phone_number')}),
        (_('Preferences'), {'fields': ('timezone', 'language')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Verification'), {'fields': ('email_verified',)}),
        (_('Important dates'), {'fields': ('last_login', 'created_at', 'updated_at')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2'),
        }),
    )

    readonly_fields = ['created_at', 'updated_at', 'last_login']


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    """API Key admin."""

    list_display = ['name', 'user', 'prefix', 'is_active', 'expires_at', 'last_used_at', 'created_at']
    list_filter = ['is_active', 'created_at', 'expires_at']
    search_fields = ['name', 'prefix', 'user__email']
    ordering = ['-created_at']

    fieldsets = (
        (None, {'fields': ('user', 'name', 'key', 'prefix')}),
        (_('Status'), {'fields': ('is_active', 'expires_at')}),
        (_('Permissions'), {'fields': ('scopes',)}),
        (_('Usage'), {'fields': ('last_used_at', 'last_used_ip')}),
        (_('Timestamps'), {'fields': ('created_at', 'updated_at')}),
    )

    readonly_fields = ['key', 'prefix', 'last_used_at', 'last_used_ip', 'created_at', 'updated_at']
