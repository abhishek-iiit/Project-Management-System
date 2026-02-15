"""
Audit log model for tracking all changes in the system.
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.fields import ArrayField

from apps.common.models import TimestampedModel

User = get_user_model()


class AuditAction(models.TextChoices):
    """Audit action type choices."""

    # CRUD operations
    CREATE = 'create', _('Create')
    READ = 'read', _('Read')
    UPDATE = 'update', _('Update')
    DELETE = 'delete', _('Delete')

    # Authentication
    LOGIN = 'login', _('Login')
    LOGOUT = 'logout', _('Logout')
    LOGIN_FAILED = 'login_failed', _('Login Failed')

    # Specific actions
    TRANSITION = 'transition', _('Transition')
    ASSIGN = 'assign', _('Assign')
    COMMENT = 'comment', _('Comment')
    ATTACH = 'attach', _('Attach')
    LINK = 'link', _('Link')
    WATCH = 'watch', _('Watch')
    UNWATCH = 'unwatch', _('Unwatch')

    # Permissions
    PERMISSION_GRANT = 'permission_grant', _('Permission Grant')
    PERMISSION_REVOKE = 'permission_revoke', _('Permission Revoke')

    # Export/Import
    EXPORT = 'export', _('Export')
    IMPORT = 'import', _('Import')


class AuditLogQuerySet(models.QuerySet):
    """Custom QuerySet for AuditLog."""

    def for_user(self, user):
        """Filter logs for a specific user."""
        return self.filter(user=user)

    def for_organization(self, organization):
        """Filter logs for an organization."""
        return self.filter(organization=organization)

    def for_entity(self, entity_type, entity_id):
        """Filter logs for a specific entity."""
        return self.filter(entity_type=entity_type, entity_id=entity_id)

    def by_action(self, action):
        """Filter by action type."""
        return self.filter(action=action)

    def recent(self, days=7):
        """Get recent logs."""
        from django.utils import timezone
        from datetime import timedelta
        since = timezone.now() - timedelta(days=days)
        return self.filter(created_at__gte=since)

    def successful(self):
        """Filter successful operations only."""
        return self.filter(success=True)

    def failed(self):
        """Filter failed operations only."""
        return self.filter(success=False)


class AuditLog(TimestampedModel):
    """
    Audit log model for tracking all system changes.

    Provides comprehensive audit trail of who did what, when, and where.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text=_('Unique identifier (UUID4)')
    )

    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        help_text=_('Organization this log belongs to')
    )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        help_text=_('User who performed the action')
    )

    # What happened
    action = models.CharField(
        max_length=50,
        choices=AuditAction.choices,
        db_index=True,
        verbose_name=_('action'),
        help_text=_('Type of action performed')
    )

    # What was affected
    entity_type = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name=_('entity type'),
        help_text=_('Type of entity affected (e.g., Issue, Project)')
    )

    entity_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('entity ID'),
        help_text=_('ID of the affected entity')
    )

    entity_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('entity name'),
        help_text=_('Name/identifier of the affected entity')
    )

    # Changes made
    changes = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('changes'),
        help_text=_('Field-level changes (old vs new values)')
    )

    # Additional context
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('metadata'),
        help_text=_('Additional metadata about the action')
    )

    # Request information
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_('IP address'),
        help_text=_('IP address of the request')
    )

    user_agent = models.TextField(
        blank=True,
        verbose_name=_('user agent'),
        help_text=_('User agent string from the request')
    )

    request_method = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_('request method'),
        help_text=_('HTTP request method (GET, POST, etc.)')
    )

    request_path = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_('request path'),
        help_text=_('URL path of the request')
    )

    # Success/failure tracking
    success = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_('success'),
        help_text=_('Whether the action succeeded')
    )

    error_message = models.TextField(
        blank=True,
        verbose_name=_('error message'),
        help_text=_('Error message if action failed')
    )

    # Duration tracking
    duration_ms = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('duration (ms)'),
        help_text=_('Duration of the operation in milliseconds')
    )

    # Tags for categorization
    tags = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True,
        verbose_name=_('tags'),
        help_text=_('Tags for categorizing logs')
    )

    objects = AuditLogQuerySet.as_manager()

    class Meta:
        db_table = 'audit_logs'
        verbose_name = _('audit log')
        verbose_name_plural = _('audit logs')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', '-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['entity_type', 'entity_id', '-created_at']),
            models.Index(fields=['action', '-created_at']),
            models.Index(fields=['success', '-created_at']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        user_str = self.user.email if self.user else 'System'
        return f"{user_str} - {self.action} {self.entity_type} ({self.created_at})"

    def get_changed_fields(self):
        """
        Get list of changed field names.

        Returns:
            List of field names that were changed
        """
        return list(self.changes.keys()) if self.changes else []

    def get_change_summary(self):
        """
        Get human-readable summary of changes.

        Returns:
            String summary of changes
        """
        if not self.changes:
            return "No changes"

        summaries = []
        for field, change in self.changes.items():
            old = change.get('from', 'None')
            new = change.get('to', 'None')
            summaries.append(f"{field}: {old} → {new}")

        return ", ".join(summaries)

    @classmethod
    def log_action(
        cls,
        action,
        entity_type,
        entity_id=None,
        entity_name='',
        changes=None,
        user=None,
        organization=None,
        metadata=None,
        ip_address=None,
        user_agent=None,
        request_method='',
        request_path='',
        success=True,
        error_message='',
        duration_ms=None,
        tags=None,
    ):
        """
        Create an audit log entry.

        Args:
            action: Action type
            entity_type: Type of entity
            entity_id: Optional entity ID
            entity_name: Optional entity name
            changes: Optional dict of changes
            user: User who performed the action
            organization: Organization context
            metadata: Additional metadata
            ip_address: Request IP address
            user_agent: Request user agent
            request_method: HTTP method
            request_path: Request path
            success: Whether action succeeded
            error_message: Error message if failed
            duration_ms: Operation duration
            tags: List of tags

        Returns:
            Created AuditLog instance
        """
        return cls.objects.create(
            organization=organization,
            user=user,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            changes=changes or {},
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent,
            request_method=request_method,
            request_path=request_path,
            success=success,
            error_message=error_message,
            duration_ms=duration_ms,
            tags=tags or [],
        )
