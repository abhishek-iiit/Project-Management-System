"""
Project models for project management.

Following CLAUDE.md best practices:
- Projects scoped to organizations
- Flexible role-based access
- Customizable settings
- Optimized queries
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from apps.common.models import BaseModel, AuditMixin


class ProjectQuerySet(models.QuerySet):
    """Custom QuerySet for Project with optimizations."""

    def active(self):
        """Filter active projects only."""
        return self.filter(is_active=True)

    def for_organization(self, organization):
        """Filter projects by organization."""
        return self.filter(organization=organization)

    def with_full_details(self):
        """
        Optimize query with all related data.

        Following CLAUDE.md best practices - ALWAYS use this for list/detail views.
        """
        return self.select_related(
            'organization',
            'created_by',
            'updated_by',
            'lead',
        ).prefetch_related(
            'members',
            'members__user',
            'project_members',
            'project_members__user',
        ).annotate(
            members_count=models.Count('project_members', filter=models.Q(project_members__is_active=True)),
            issues_count=models.Count('issues', filter=models.Q(issues__deleted_at__isnull=True)),
        )


class Project(BaseModel, AuditMixin):
    """
    Project model - container for issues and work items.

    Projects belong to organizations and have members with specific roles.
    """

    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='projects',
        db_index=True,
        help_text=_('Organization this project belongs to')
    )

    name = models.CharField(
        _('name'),
        max_length=255,
        help_text=_('Project name')
    )

    key = models.CharField(
        _('key'),
        max_length=10,
        db_index=True,
        validators=[
            RegexValidator(
                regex=r'^[A-Z][A-Z0-9]{1,9}$',
                message=_('Key must start with a letter and contain only uppercase letters and numbers')
            )
        ],
        help_text=_('Unique project key (e.g., PROJ, BUG) - used in issue keys')
    )

    description = models.TextField(
        _('description'),
        blank=True,
        help_text=_('Project description')
    )

    avatar = models.URLField(
        _('avatar URL'),
        blank=True,
        null=True,
        help_text=_('URL to project avatar/logo')
    )

    # Project lead
    lead = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='led_projects',
        help_text=_('Project lead/manager')
    )

    # Project type
    PROJECT_TYPE_CHOICES = [
        ('software', _('Software')),
        ('business', _('Business')),
        ('marketing', _('Marketing')),
        ('operations', _('Operations')),
        ('other', _('Other')),
    ]

    project_type = models.CharField(
        _('project type'),
        max_length=20,
        choices=PROJECT_TYPE_CHOICES,
        default='software',
        help_text=_('Type of project')
    )

    # Project template/style
    TEMPLATE_CHOICES = [
        ('scrum', _('Scrum')),
        ('kanban', _('Kanban')),
        ('basic', _('Basic')),
    ]

    template = models.CharField(
        _('template'),
        max_length=20,
        choices=TEMPLATE_CHOICES,
        default='basic',
        help_text=_('Project template/methodology')
    )

    # Settings (JSONB for flexibility)
    settings = models.JSONField(
        _('settings'),
        default=dict,
        blank=True,
        help_text=_('Project-specific settings (workflows, fields, permissions, etc.)')
    )

    # Status
    is_active = models.BooleanField(
        _('is active'),
        default=True,
        db_index=True,
        help_text=_('Whether this project is active')
    )

    is_private = models.BooleanField(
        _('is private'),
        default=False,
        help_text=_('Whether this project is private (only members can see)')
    )

    # Members relationship
    members = models.ManyToManyField(
        'accounts.User',
        through='ProjectMember',
        through_fields=('project', 'user'),
        related_name='member_projects',
        help_text=_('Users who are members of this project')
    )

    objects = ProjectQuerySet.as_manager()

    class Meta:
        db_table = 'projects'
        verbose_name = _('project')
        verbose_name_plural = _('projects')
        ordering = ['-created_at']
        unique_together = [['organization', 'key']]
        indexes = [
            models.Index(fields=['organization', 'key']),
            models.Index(fields=['organization', 'is_active']),
            models.Index(fields=['is_active', 'name']),
        ]

    def __str__(self):
        """String representation."""
        return f"{self.key} - {self.name}"

    def __repr__(self):
        """Developer-friendly representation."""
        return f"<Project key={self.key} org={self.organization.slug}>"

    def get_member_count(self):
        """
        Get count of active members.

        Returns:
            Integer count of active members
        """
        return self.project_members.filter(is_active=True).count()

    def get_issue_count(self):
        """
        Get count of issues in this project.

        Returns:
            Integer count of issues
        """
        return self.issues.filter(deleted_at__isnull=True).count()

    def get_admins(self):
        """
        Get all admins of this project.

        Returns:
            QuerySet of User instances
        """
        return self.members.filter(
            project_members__is_admin=True,
            project_members__is_active=True
        )

    def add_member(self, user, role=None, is_admin=False):
        """
        Add a user to this project.

        Args:
            user: User instance to add
            role: Optional ProjectRole instance
            is_admin: Whether user is project admin

        Returns:
            ProjectMember instance
        """
        return ProjectMember.objects.create(
            project=self,
            user=user,
            role=role,
            is_admin=is_admin
        )

    def remove_member(self, user):
        """
        Remove a user from this project (soft delete).

        Args:
            user: User instance to remove
        """
        try:
            membership = ProjectMember.objects.get(
                project=self,
                user=user
            )
            membership.delete()  # Soft delete
        except ProjectMember.DoesNotExist:
            pass

    def has_member(self, user):
        """
        Check if user is a member of this project.

        Args:
            user: User instance

        Returns:
            Boolean
        """
        return ProjectMember.objects.filter(
            project=self,
            user=user,
            is_active=True
        ).exists()

    def is_member_admin(self, user):
        """
        Check if user is an admin of this project.

        Args:
            user: User instance

        Returns:
            Boolean
        """
        try:
            membership = ProjectMember.objects.get(
                project=self,
                user=user,
                is_active=True
            )
            return membership.is_admin
        except ProjectMember.DoesNotExist:
            return False


class ProjectRole(BaseModel, AuditMixin):
    """
    Project role definition.

    Defines roles that can be assigned to project members.
    Each project can have custom roles or use default ones.
    """

    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='project_roles',
        help_text=_('Organization this role belongs to')
    )

    name = models.CharField(
        _('name'),
        max_length=100,
        help_text=_('Role name (e.g., Developer, Viewer, Admin)')
    )

    description = models.TextField(
        _('description'),
        blank=True,
        help_text=_('Role description')
    )

    # Permissions (JSONB for flexibility)
    permissions = models.JSONField(
        _('permissions'),
        default=dict,
        blank=True,
        help_text=_('Role permissions configuration')
    )

    is_default = models.BooleanField(
        _('is default'),
        default=False,
        help_text=_('Whether this is a default role for new projects')
    )

    class Meta:
        db_table = 'project_roles'
        verbose_name = _('project role')
        verbose_name_plural = _('project roles')
        ordering = ['name']
        unique_together = [['organization', 'name']]
        indexes = [
            models.Index(fields=['organization', 'name']),
            models.Index(fields=['organization', 'is_default']),
        ]

    def __str__(self):
        """String representation."""
        return self.name

    def __repr__(self):
        """Developer-friendly representation."""
        return f"<ProjectRole name={self.name} org={self.organization.slug}>"

    def has_permission(self, permission_key):
        """
        Check if role has a specific permission.

        Args:
            permission_key: Permission key to check (e.g., 'create_issue', 'delete_issue')

        Returns:
            Boolean
        """
        return self.permissions.get(permission_key, False)


class ProjectMember(BaseModel, AuditMixin):
    """
    Project membership - links users to projects with roles.

    Defines what role a user has in a project.
    """

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='project_members',
        help_text=_('Project this membership belongs to')
    )

    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='project_memberships',
        help_text=_('User who is a member')
    )

    role = models.ForeignKey(
        ProjectRole,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members',
        help_text=_('Role assigned to this member')
    )

    is_admin = models.BooleanField(
        _('is admin'),
        default=False,
        db_index=True,
        help_text=_('Whether this member is a project admin')
    )

    is_active = models.BooleanField(
        _('is active'),
        default=True,
        db_index=True,
        help_text=_('Whether this membership is active')
    )

    # Custom permissions override (JSONB)
    custom_permissions = models.JSONField(
        _('custom permissions'),
        default=dict,
        blank=True,
        help_text=_('Custom permissions for this specific member')
    )

    class Meta:
        db_table = 'project_members'
        verbose_name = _('project member')
        verbose_name_plural = _('project members')
        ordering = ['project', 'user']
        unique_together = [['project', 'user']]
        indexes = [
            models.Index(fields=['project', 'user']),
            models.Index(fields=['project', 'is_active']),
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['project', 'is_admin', 'is_active']),
        ]

    def __str__(self):
        """String representation."""
        role_name = self.role.name if self.role else 'No Role'
        return f"{self.user.email} - {self.project.key} ({role_name})"

    def __repr__(self):
        """Developer-friendly representation."""
        return f"<ProjectMember project={self.project.key} user={self.user.email}>"

    def has_permission(self, permission_key):
        """
        Check if member has a specific permission.

        Checks custom permissions first, then role permissions.

        Args:
            permission_key: Permission key to check

        Returns:
            Boolean
        """
        # Admins have all permissions
        if self.is_admin:
            return True

        # Check custom permissions override
        if permission_key in self.custom_permissions:
            return self.custom_permissions[permission_key]

        # Check role permissions
        if self.role:
            return self.role.has_permission(permission_key)

        return False


class ProjectTemplate(BaseModel):
    """
    Project template for quick project creation.

    Templates define default settings, roles, workflows, etc.
    """

    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='project_templates',
        help_text=_('Organization this template belongs to')
    )

    name = models.CharField(
        _('name'),
        max_length=100,
        help_text=_('Template name')
    )

    description = models.TextField(
        _('description'),
        blank=True,
        help_text=_('Template description')
    )

    template_type = models.CharField(
        _('template type'),
        max_length=20,
        choices=Project.TEMPLATE_CHOICES,
        default='basic',
        help_text=_('Template type')
    )

    # Template configuration (JSONB)
    config = models.JSONField(
        _('configuration'),
        default=dict,
        blank=True,
        help_text=_('Template configuration (default settings, roles, workflows, etc.)')
    )

    is_default = models.BooleanField(
        _('is default'),
        default=False,
        help_text=_('Whether this is the default template')
    )

    class Meta:
        db_table = 'project_templates'
        verbose_name = _('project template')
        verbose_name_plural = _('project templates')
        ordering = ['name']
        indexes = [
            models.Index(fields=['organization', 'is_default']),
        ]

    def __str__(self):
        """String representation."""
        return self.name

    def __repr__(self):
        """Developer-friendly representation."""
        return f"<ProjectTemplate name={self.name} org={self.organization.slug}>"
