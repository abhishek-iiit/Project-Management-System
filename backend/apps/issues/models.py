"""
Issue models for issue tracking.

Following CLAUDE.md best practices:
- Fat models with business logic
- Optimized QuerySets
- JSONB for flexible custom fields
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db.models import Q, Count, Max
from apps.common.models import BaseModel, AuditMixin
import re


class IssueType(BaseModel, AuditMixin):
    """
    Issue type definition (Story, Task, Bug, Epic, Subtask, etc.).

    Issue types are configurable per organization.
    """

    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='issue_types',
        help_text=_('Organization this issue type belongs to')
    )

    name = models.CharField(
        _('name'),
        max_length=100,
        help_text=_('Issue type name (e.g., Story, Task, Bug, Epic)')
    )

    description = models.TextField(
        _('description'),
        blank=True,
        help_text=_('Issue type description')
    )

    icon = models.CharField(
        _('icon'),
        max_length=50,
        blank=True,
        help_text=_('Icon identifier for UI')
    )

    color = models.CharField(
        _('color'),
        max_length=7,
        blank=True,
        help_text=_('Color hex code (e.g., #FF5733)')
    )

    is_subtask = models.BooleanField(
        _('is subtask'),
        default=False,
        help_text=_('Whether this is a subtask type')
    )

    is_epic = models.BooleanField(
        _('is epic'),
        default=False,
        help_text=_('Whether this is an epic type')
    )

    is_default = models.BooleanField(
        _('is default'),
        default=False,
        help_text=_('Whether this is the default issue type')
    )

    is_active = models.BooleanField(
        _('is active'),
        default=True,
        db_index=True,
        help_text=_('Whether this issue type is active')
    )

    position = models.PositiveIntegerField(
        _('position'),
        default=0,
        help_text=_('Display order')
    )

    class Meta:
        db_table = 'issue_types'
        verbose_name = _('issue type')
        verbose_name_plural = _('issue types')
        ordering = ['organization', 'position', 'name']
        unique_together = [['organization', 'name']]
        indexes = [
            models.Index(fields=['organization', 'name']),
            models.Index(fields=['organization', 'is_active']),
            models.Index(fields=['organization', 'is_default']),
        ]

    def __str__(self):
        """String representation."""
        return f"{self.name} ({self.organization.name})"

    def __repr__(self):
        """Developer-friendly representation."""
        return f"<IssueType name={self.name} org={self.organization.name}>"


class Priority(BaseModel, AuditMixin):
    """
    Issue priority definition (Blocker, High, Medium, Low, etc.).

    Priorities are configurable per organization.
    """

    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='priorities',
        help_text=_('Organization this priority belongs to')
    )

    name = models.CharField(
        _('name'),
        max_length=100,
        help_text=_('Priority name (e.g., Blocker, High, Medium, Low)')
    )

    description = models.TextField(
        _('description'),
        blank=True,
        help_text=_('Priority description')
    )

    icon = models.CharField(
        _('icon'),
        max_length=50,
        blank=True,
        help_text=_('Icon identifier for UI')
    )

    color = models.CharField(
        _('color'),
        max_length=7,
        blank=True,
        help_text=_('Color hex code (e.g., #FF0000)')
    )

    level = models.PositiveIntegerField(
        _('level'),
        default=3,
        help_text=_('Priority level (1=highest, 5=lowest)')
    )

    is_default = models.BooleanField(
        _('is default'),
        default=False,
        help_text=_('Whether this is the default priority')
    )

    is_active = models.BooleanField(
        _('is active'),
        default=True,
        db_index=True,
        help_text=_('Whether this priority is active')
    )

    class Meta:
        db_table = 'priorities'
        verbose_name = _('priority')
        verbose_name_plural = _('priorities')
        ordering = ['organization', 'level', 'name']
        unique_together = [['organization', 'name']]
        indexes = [
            models.Index(fields=['organization', 'name']),
            models.Index(fields=['organization', 'level']),
            models.Index(fields=['organization', 'is_default']),
        ]

    def __str__(self):
        """String representation."""
        return f"{self.name} ({self.organization.name})"

    def __repr__(self):
        """Developer-friendly representation."""
        return f"<Priority name={self.name} level={self.level}>"


class IssueQuerySet(models.QuerySet):
    """Optimized queries for Issue model."""

    def active(self):
        """Filter active issues only."""
        return self.filter(deleted_at__isnull=True)

    def for_project(self, project):
        """Filter issues by project."""
        if hasattr(project, 'id'):
            project = project.id
        return self.filter(project_id=project)

    def for_organization(self, organization):
        """Filter issues by organization."""
        if hasattr(organization, 'id'):
            organization = organization.id
        return self.filter(project__organization_id=organization)

    def with_full_details(self):
        """Optimize query with all related data."""
        return self.select_related(
            'project',
            'project__organization',
            'issue_type',
            'priority',
            'status',
            'reporter',
            'assignee',
            'epic',
            'parent',
            'created_by',
            'updated_by',
        ).prefetch_related(
            'labels',
            'watchers',
            'watchers__user',
            'attachments',
            'comments',
            'comments__user',
            'linked_issues',
            'linked_issues__to_issue',
        )

    def open_issues(self):
        """Get open issues (not in Done category)."""
        return self.exclude(status__category='done')

    def closed_issues(self):
        """Get closed issues (in Done category)."""
        return self.filter(status__category='done')


class Issue(BaseModel, AuditMixin):
    """
    Core issue model with dynamic custom fields.

    Supports:
    - Dynamic custom fields via JSONB
    - Issue hierarchy (Epic > Story > Task > Subtask)
    - Issue linking
    - Watchers
    - Attachments and comments
    """

    # Project and type
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='issues',
        help_text=_('Project this issue belongs to')
    )

    issue_type = models.ForeignKey(
        IssueType,
        on_delete=models.PROTECT,
        related_name='issues',
        help_text=_('Issue type')
    )

    # Unique key within project (e.g., PROJ-123)
    key = models.CharField(
        _('key'),
        max_length=50,
        unique=True,
        db_index=True,
        help_text=_('Unique issue key (e.g., PROJ-123)')
    )

    # Basic fields
    summary = models.CharField(
        _('summary'),
        max_length=500,
        help_text=_('Issue summary/title')
    )

    description = models.TextField(
        _('description'),
        blank=True,
        help_text=_('Detailed description')
    )

    # Workflow
    status = models.ForeignKey(
        'workflows.Status',
        on_delete=models.PROTECT,
        related_name='issues',
        help_text=_('Current status')
    )

    # Priority
    priority = models.ForeignKey(
        Priority,
        on_delete=models.PROTECT,
        related_name='issues',
        null=True,
        blank=True,
        help_text=_('Issue priority')
    )

    # Assignment
    reporter = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='reported_issues',
        help_text=_('User who reported this issue')
    )

    assignee = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        related_name='assigned_issues',
        null=True,
        blank=True,
        help_text=_('User assigned to this issue')
    )

    # Hierarchy
    epic = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        related_name='epic_children',
        null=True,
        blank=True,
        help_text=_('Parent epic')
    )

    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_name='subtasks',
        null=True,
        blank=True,
        help_text=_('Parent issue (for subtasks)')
    )

    # Time tracking
    original_estimate = models.PositiveIntegerField(
        _('original estimate'),
        null=True,
        blank=True,
        help_text=_('Original time estimate in minutes')
    )

    remaining_estimate = models.PositiveIntegerField(
        _('remaining estimate'),
        null=True,
        blank=True,
        help_text=_('Remaining time estimate in minutes')
    )

    time_spent = models.PositiveIntegerField(
        _('time spent'),
        default=0,
        help_text=_('Time spent in minutes')
    )

    # Dates
    due_date = models.DateField(
        _('due date'),
        null=True,
        blank=True,
        help_text=_('Due date for this issue')
    )

    resolution_date = models.DateTimeField(
        _('resolution date'),
        null=True,
        blank=True,
        help_text=_('When the issue was resolved')
    )

    # Resolution
    resolution = models.CharField(
        _('resolution'),
        max_length=100,
        blank=True,
        help_text=_('Resolution (e.g., Fixed, Won\'t Fix, Duplicate)')
    )

    # Custom fields (JSONB for flexibility)
    custom_field_values = models.JSONField(
        _('custom field values'),
        default=dict,
        blank=True,
        help_text=_('Dynamic custom field values')
    )

    # Sprints (M2M - will be defined in boards app)
    # sprints = models.ManyToManyField('boards.Sprint', related_name='issues')

    # Labels (simple tags)
    labels = models.ManyToManyField(
        'Label',
        related_name='issues',
        blank=True,
        help_text=_('Issue labels/tags')
    )

    # Objects manager
    objects = IssueQuerySet.as_manager()

    class Meta:
        db_table = 'issues'
        verbose_name = _('issue')
        verbose_name_plural = _('issues')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', 'key']),
            models.Index(fields=['project', 'status']),
            models.Index(fields=['project', 'issue_type']),
            models.Index(fields=['project', 'assignee']),
            models.Index(fields=['project', 'reporter']),
            models.Index(fields=['assignee', 'status']),
            models.Index(fields=['epic']),
            models.Index(fields=['parent']),
            models.Index(fields=['due_date']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        """String representation."""
        return f"{self.key}: {self.summary}"

    def __repr__(self):
        """Developer-friendly representation."""
        return f"<Issue key={self.key} status={self.status.name}>"

    def save(self, *args, **kwargs):
        """Override save to generate key if needed."""
        if not self.key:
            self.key = self._generate_key()
        super().save(*args, **kwargs)

    def _generate_key(self):
        """
        Generate unique issue key.

        Format: PROJECT_KEY-NUMBER (e.g., PROJ-123)
        """
        project_key = self.project.key

        # Get the last issue number for this project
        last_issue = Issue.objects.filter(
            project=self.project
        ).aggregate(
            max_num=Max('id')
        )

        # Extract number from last key or start from 1
        if last_issue['max_num']:
            next_num = Issue.objects.filter(project=self.project).count() + 1
        else:
            next_num = 1

        return f"{project_key}-{next_num}"

    def is_subtask(self):
        """Check if this is a subtask."""
        return self.parent is not None or self.issue_type.is_subtask

    def is_epic(self):
        """Check if this is an epic."""
        return self.issue_type.is_epic

    def get_subtasks(self):
        """Get all subtasks of this issue."""
        return self.subtasks.active()

    def get_epic_children(self):
        """Get all issues in this epic."""
        return self.epic_children.active()

    def can_transition_to(self, status, user):
        """
        Check if issue can transition to a specific status.

        Args:
            status: Target Status instance
            user: User attempting the transition

        Returns:
            Boolean
        """
        from apps.workflows.services import WorkflowEngine

        engine = WorkflowEngine(user=user)
        transitions = engine.get_available_transitions(self, user)

        return any(t.to_status == status for t in transitions)

    def add_watcher(self, user):
        """
        Add a user as a watcher.

        Args:
            user: User instance
        """
        Watcher.objects.get_or_create(
            issue=self,
            user=user
        )

    def remove_watcher(self, user):
        """
        Remove a user from watchers.

        Args:
            user: User instance
        """
        Watcher.objects.filter(
            issue=self,
            user=user
        ).delete()

    def is_watcher(self, user):
        """
        Check if user is watching this issue.

        Args:
            user: User instance

        Returns:
            Boolean
        """
        return self.watchers.filter(user=user).exists()


class Label(BaseModel):
    """
    Label/tag for categorizing issues.

    Labels are scoped to projects or organizations.
    """

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='labels',
        null=True,
        blank=True,
        help_text=_('Project this label belongs to (null for org-wide)')
    )

    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='labels',
        help_text=_('Organization this label belongs to')
    )

    name = models.CharField(
        _('name'),
        max_length=100,
        help_text=_('Label name')
    )

    color = models.CharField(
        _('color'),
        max_length=7,
        blank=True,
        help_text=_('Color hex code')
    )

    class Meta:
        db_table = 'labels'
        verbose_name = _('label')
        verbose_name_plural = _('labels')
        ordering = ['organization', 'name']
        indexes = [
            models.Index(fields=['organization', 'name']),
            models.Index(fields=['project', 'name']),
        ]

    def __str__(self):
        """String representation."""
        scope = self.project.key if self.project else self.organization.name
        return f"{self.name} ({scope})"


class Comment(BaseModel, AuditMixin):
    """
    Comment on an issue.

    Supports mentions, formatting, and attachments.
    """

    issue = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        related_name='comments',
        help_text=_('Issue this comment belongs to')
    )

    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='issue_comments',
        help_text=_('User who made this comment')
    )

    body = models.TextField(
        _('body'),
        help_text=_('Comment text (supports markdown)')
    )

    # Mentions (extracted from body)
    mentions = models.ManyToManyField(
        'accounts.User',
        related_name='mentioned_in_comments',
        blank=True,
        help_text=_('Users mentioned in this comment')
    )

    class Meta:
        db_table = 'issue_comments'
        verbose_name = _('comment')
        verbose_name_plural = _('comments')
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['issue', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        """String representation."""
        return f"Comment on {self.issue.key} by {self.user.email}"

    def extract_mentions(self):
        """
        Extract user mentions from comment body.

        Mentions format: @username or @"User Name"
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()

        # Pattern for @username or @"Full Name"
        pattern = r'@(\w+)|@"([^"]+)"'
        matches = re.findall(pattern, self.body)

        mentioned_users = []
        for username, full_name in matches:
            identifier = username or full_name
            try:
                # Try to find user by username or email
                user = User.objects.get(
                    Q(username=identifier) | Q(email=identifier)
                )
                mentioned_users.append(user)
            except User.DoesNotExist:
                continue

        # Update mentions
        if mentioned_users:
            self.mentions.set(mentioned_users)


class Attachment(BaseModel, AuditMixin):
    """
    File attachment for an issue.

    Supports various file types with metadata.
    """

    issue = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        related_name='attachments',
        help_text=_('Issue this attachment belongs to')
    )

    file = models.FileField(
        _('file'),
        upload_to='issue_attachments/%Y/%m/%d/',
        help_text=_('Uploaded file')
    )

    filename = models.CharField(
        _('filename'),
        max_length=255,
        help_text=_('Original filename')
    )

    file_size = models.PositiveIntegerField(
        _('file size'),
        help_text=_('File size in bytes')
    )

    mime_type = models.CharField(
        _('mime type'),
        max_length=100,
        blank=True,
        help_text=_('MIME type of the file')
    )

    class Meta:
        db_table = 'issue_attachments'
        verbose_name = _('attachment')
        verbose_name_plural = _('attachments')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['issue', '-created_at']),
        ]

    def __str__(self):
        """String representation."""
        return f"{self.filename} ({self.issue.key})"

    def get_file_extension(self):
        """Get file extension."""
        import os
        return os.path.splitext(self.filename)[1].lower()

    def is_image(self):
        """Check if attachment is an image."""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        return self.get_file_extension() in image_extensions


class IssueLinkType(BaseModel):
    """
    Type of relationship between issues.

    Examples: blocks, relates to, duplicates, etc.
    """

    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='issue_link_types',
        help_text=_('Organization this link type belongs to')
    )

    name = models.CharField(
        _('name'),
        max_length=100,
        help_text=_('Link type name (e.g., blocks, relates to)')
    )

    inward_description = models.CharField(
        _('inward description'),
        max_length=100,
        help_text=_('Description from target to source (e.g., "is blocked by")')
    )

    outward_description = models.CharField(
        _('outward description'),
        max_length=100,
        help_text=_('Description from source to target (e.g., "blocks")')
    )

    is_active = models.BooleanField(
        _('is active'),
        default=True,
        help_text=_('Whether this link type is active')
    )

    class Meta:
        db_table = 'issue_link_types'
        verbose_name = _('issue link type')
        verbose_name_plural = _('issue link types')
        ordering = ['organization', 'name']
        unique_together = [['organization', 'name']]
        indexes = [
            models.Index(fields=['organization', 'name']),
        ]

    def __str__(self):
        """String representation."""
        return f"{self.name} ({self.organization.name})"


class IssueLink(BaseModel, AuditMixin):
    """
    Link between two issues.

    Represents relationships like "blocks", "relates to", etc.
    """

    from_issue = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        related_name='outward_links',
        help_text=_('Source issue')
    )

    to_issue = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        related_name='inward_links',
        help_text=_('Target issue')
    )

    link_type = models.ForeignKey(
        IssueLinkType,
        on_delete=models.PROTECT,
        related_name='links',
        help_text=_('Type of relationship')
    )

    class Meta:
        db_table = 'issue_links'
        verbose_name = _('issue link')
        verbose_name_plural = _('issue links')
        ordering = ['from_issue', 'link_type']
        unique_together = [['from_issue', 'to_issue', 'link_type']]
        indexes = [
            models.Index(fields=['from_issue', 'link_type']),
            models.Index(fields=['to_issue', 'link_type']),
        ]

    def __str__(self):
        """String representation."""
        return f"{self.from_issue.key} {self.link_type.outward_description} {self.to_issue.key}"

    def clean(self):
        """Validate link."""
        super().clean()

        # Cannot link issue to itself
        if self.from_issue == self.to_issue:
            raise ValidationError({
                'to_issue': _('Cannot link issue to itself')
            })

        # Check if issues belong to same organization
        if self.from_issue.project.organization != self.to_issue.project.organization:
            raise ValidationError({
                'to_issue': _('Can only link issues within the same organization')
            })


class Watcher(BaseModel):
    """
    User watching an issue for updates.

    Watchers receive notifications about issue changes.
    """

    issue = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        related_name='watchers',
        help_text=_('Issue being watched')
    )

    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='watched_issues',
        help_text=_('User watching the issue')
    )

    class Meta:
        db_table = 'issue_watchers'
        verbose_name = _('watcher')
        verbose_name_plural = _('watchers')
        ordering = ['issue', 'user']
        unique_together = [['issue', 'user']]
        indexes = [
            models.Index(fields=['issue']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        """String representation."""
        return f"{self.user.email} watching {self.issue.key}"
