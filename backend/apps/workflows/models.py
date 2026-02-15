"""
Workflow models for state machine functionality.

Following CLAUDE.md best practices:
- Fat models with business logic
- Optimized QuerySets
- JSONB for flexible configurations
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from apps.common.models import BaseModel, AuditMixin


class StatusCategory(models.TextChoices):
    """Standard status categories for grouping statuses."""
    TODO = 'todo', _('To Do')
    IN_PROGRESS = 'in_progress', _('In Progress')
    DONE = 'done', _('Done')


class WorkflowQuerySet(models.QuerySet):
    """Optimized queries for Workflow model."""

    def active(self):
        """Filter active workflows only."""
        return self.filter(is_active=True)

    def for_organization(self, organization):
        """Filter workflows by organization."""
        if hasattr(organization, 'id'):
            organization = organization.id
        return self.filter(organization_id=organization)

    def with_full_details(self):
        """Optimize query with all related data."""
        return self.select_related(
            'organization',
            'created_by',
            'updated_by',
        ).prefetch_related(
            'statuses',
            'transitions',
            'transitions__from_status',
            'transitions__to_status',
        )


class Workflow(BaseModel, AuditMixin):
    """
    Workflow definition - a state machine for issues.

    A workflow defines the possible states (statuses) and allowed
    transitions between them. Workflows are reusable across projects.
    """

    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='workflows',
        help_text=_('Organization this workflow belongs to')
    )

    name = models.CharField(
        _('name'),
        max_length=100,
        help_text=_('Workflow name (e.g., Simple Workflow, Scrum Workflow)')
    )

    description = models.TextField(
        _('description'),
        blank=True,
        help_text=_('Workflow description')
    )

    is_active = models.BooleanField(
        _('is active'),
        default=True,
        db_index=True,
        help_text=_('Whether this workflow is active')
    )

    is_default = models.BooleanField(
        _('is default'),
        default=False,
        help_text=_('Whether this is the default workflow for new projects')
    )

    # Objects manager
    objects = WorkflowQuerySet.as_manager()

    class Meta:
        db_table = 'workflows'
        verbose_name = _('workflow')
        verbose_name_plural = _('workflows')
        ordering = ['organization', 'name']
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
        return f"<Workflow name={self.name} org={self.organization.name}>"

    def get_initial_status(self):
        """
        Get the initial status for this workflow.

        Returns:
            Status instance or None
        """
        return self.statuses.filter(is_initial=True).first()

    def get_statuses_by_category(self, category):
        """
        Get all statuses in a specific category.

        Args:
            category: StatusCategory value

        Returns:
            QuerySet of Status instances
        """
        return self.statuses.filter(category=category, is_active=True)

    def get_available_transitions(self, from_status, user=None):
        """
        Get available transitions from a specific status.

        Args:
            from_status: Status instance or None (for initial)
            user: Optional User instance for permission checks

        Returns:
            QuerySet of Transition instances
        """
        transitions = self.transitions.filter(
            from_status=from_status,
            is_active=True
        ).select_related('to_status')

        # TODO: Filter by user permissions when implemented
        return transitions

    def clone(self, new_name, organization=None):
        """
        Clone this workflow with all statuses and transitions.

        Args:
            new_name: Name for the new workflow
            organization: Optional organization (defaults to same)

        Returns:
            New Workflow instance
        """
        org = organization or self.organization

        # Create new workflow
        new_workflow = Workflow.objects.create(
            organization=org,
            name=new_name,
            description=f"Cloned from {self.name}",
            is_active=True,
            is_default=False,
            created_by=self.created_by
        )

        # Clone statuses
        status_mapping = {}
        for status in self.statuses.all():
            new_status = Status.objects.create(
                workflow=new_workflow,
                name=status.name,
                description=status.description,
                category=status.category,
                is_initial=status.is_initial,
                is_active=status.is_active,
                created_by=self.created_by
            )
            status_mapping[status.id] = new_status

        # Clone transitions
        for transition in self.transitions.all():
            Transition.objects.create(
                workflow=new_workflow,
                name=transition.name,
                description=transition.description,
                from_status=status_mapping.get(transition.from_status_id) if transition.from_status_id else None,
                to_status=status_mapping[transition.to_status_id],
                conditions=transition.conditions,
                validators=transition.validators,
                post_functions=transition.post_functions,
                is_active=transition.is_active,
                created_by=self.created_by
            )

        return new_workflow


class Status(BaseModel, AuditMixin):
    """
    Status definition - a state in a workflow.

    Statuses represent the current state of an issue (e.g., Open, In Progress, Done).
    """

    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name='statuses',
        help_text=_('Workflow this status belongs to')
    )

    name = models.CharField(
        _('name'),
        max_length=100,
        help_text=_('Status name (e.g., Open, In Progress, Done)')
    )

    description = models.TextField(
        _('description'),
        blank=True,
        help_text=_('Status description')
    )

    category = models.CharField(
        _('category'),
        max_length=20,
        choices=StatusCategory.choices,
        default=StatusCategory.TODO,
        db_index=True,
        help_text=_('Status category for grouping')
    )

    is_initial = models.BooleanField(
        _('is initial'),
        default=False,
        help_text=_('Whether this is the initial status for new issues')
    )

    is_active = models.BooleanField(
        _('is active'),
        default=True,
        db_index=True,
        help_text=_('Whether this status is active')
    )

    # Display order within workflow
    position = models.PositiveIntegerField(
        _('position'),
        default=0,
        help_text=_('Display order within workflow')
    )

    class Meta:
        db_table = 'workflow_statuses'
        verbose_name = _('status')
        verbose_name_plural = _('statuses')
        ordering = ['workflow', 'position', 'name']
        unique_together = [['workflow', 'name']]
        indexes = [
            models.Index(fields=['workflow', 'name']),
            models.Index(fields=['workflow', 'category']),
            models.Index(fields=['workflow', 'is_initial']),
            models.Index(fields=['workflow', 'position']),
        ]

    def __str__(self):
        """String representation."""
        return f"{self.name} ({self.workflow.name})"

    def __repr__(self):
        """Developer-friendly representation."""
        return f"<Status name={self.name} workflow={self.workflow.name} category={self.category}>"

    def clean(self):
        """Validate status configuration."""
        super().clean()

        # Ensure only one initial status per workflow
        if self.is_initial:
            existing_initial = Status.objects.filter(
                workflow=self.workflow,
                is_initial=True
            ).exclude(id=self.id)

            if existing_initial.exists():
                raise ValidationError({
                    'is_initial': _('Only one initial status allowed per workflow')
                })

    def get_outgoing_transitions(self):
        """
        Get all transitions from this status.

        Returns:
            QuerySet of Transition instances
        """
        return Transition.objects.filter(
            from_status=self,
            is_active=True
        ).select_related('to_status')

    def get_incoming_transitions(self):
        """
        Get all transitions to this status.

        Returns:
            QuerySet of Transition instances
        """
        return Transition.objects.filter(
            to_status=self,
            is_active=True
        ).select_related('from_status')


class Transition(BaseModel, AuditMixin):
    """
    Transition definition - allowed movement between statuses.

    Transitions define the rules for moving an issue from one status
    to another, including conditions, validators, and post-functions.
    """

    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name='transitions',
        help_text=_('Workflow this transition belongs to')
    )

    name = models.CharField(
        _('name'),
        max_length=100,
        help_text=_('Transition name (e.g., Start Progress, Resolve, Close)')
    )

    description = models.TextField(
        _('description'),
        blank=True,
        help_text=_('Transition description')
    )

    from_status = models.ForeignKey(
        Status,
        on_delete=models.CASCADE,
        related_name='outgoing_transitions',
        null=True,
        blank=True,
        help_text=_('Source status (null for initial transition)')
    )

    to_status = models.ForeignKey(
        Status,
        on_delete=models.CASCADE,
        related_name='incoming_transitions',
        help_text=_('Destination status')
    )

    # Conditions (JSONB) - must be met for transition to be available
    conditions = models.JSONField(
        _('conditions'),
        default=dict,
        blank=True,
        help_text=_('Conditions that must be met (e.g., user in role, field has value)')
    )

    # Validators (JSONB) - validation rules before transition executes
    validators = models.JSONField(
        _('validators'),
        default=dict,
        blank=True,
        help_text=_('Validation rules (e.g., field required, resolution required)')
    )

    # Post-functions (JSONB) - actions to execute after transition
    post_functions = models.JSONField(
        _('post_functions'),
        default=dict,
        blank=True,
        help_text=_('Actions to execute after transition (e.g., assign to user, send email)')
    )

    is_active = models.BooleanField(
        _('is active'),
        default=True,
        db_index=True,
        help_text=_('Whether this transition is active')
    )

    # Display order
    position = models.PositiveIntegerField(
        _('position'),
        default=0,
        help_text=_('Display order in UI')
    )

    class Meta:
        db_table = 'workflow_transitions'
        verbose_name = _('transition')
        verbose_name_plural = _('transitions')
        ordering = ['workflow', 'position', 'name']
        indexes = [
            models.Index(fields=['workflow', 'from_status']),
            models.Index(fields=['workflow', 'to_status']),
            models.Index(fields=['workflow', 'is_active']),
            models.Index(fields=['from_status', 'to_status']),
        ]

    def __str__(self):
        """String representation."""
        from_name = self.from_status.name if self.from_status else 'Initial'
        return f"{self.name}: {from_name} → {self.to_status.name}"

    def __repr__(self):
        """Developer-friendly representation."""
        from_name = self.from_status.name if self.from_status else 'Initial'
        return f"<Transition {from_name} → {self.to_status.name} workflow={self.workflow.name}>"

    def clean(self):
        """Validate transition configuration."""
        super().clean()

        # Validate from_status and to_status belong to same workflow
        if self.from_status and self.from_status.workflow != self.workflow:
            raise ValidationError({
                'from_status': _('From status must belong to the same workflow')
            })

        if self.to_status.workflow != self.workflow:
            raise ValidationError({
                'to_status': _('To status must belong to the same workflow')
            })

        # Validate conditions structure
        if self.conditions and not isinstance(self.conditions, dict):
            raise ValidationError({
                'conditions': _('Conditions must be a dictionary')
            })

        # Validate validators structure
        if self.validators and not isinstance(self.validators, dict):
            raise ValidationError({
                'validators': _('Validators must be a dictionary')
            })

        # Validate post_functions structure
        if self.post_functions and not isinstance(self.post_functions, dict):
            raise ValidationError({
                'post_functions': _('Post-functions must be a dictionary')
            })


class WorkflowScheme(BaseModel, AuditMixin):
    """
    Workflow scheme - maps issue types to workflows for a project.

    A scheme allows different issue types in a project to use different
    workflows (e.g., Bugs use Bug Workflow, Stories use Scrum Workflow).
    """

    project = models.OneToOneField(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='workflow_scheme',
        help_text=_('Project this scheme belongs to')
    )

    name = models.CharField(
        _('name'),
        max_length=100,
        help_text=_('Scheme name')
    )

    description = models.TextField(
        _('description'),
        blank=True,
        help_text=_('Scheme description')
    )

    # Default workflow for issue types not explicitly mapped
    default_workflow = models.ForeignKey(
        Workflow,
        on_delete=models.PROTECT,
        related_name='default_for_schemes',
        help_text=_('Default workflow for unmapped issue types')
    )

    # Issue type to workflow mappings (JSONB)
    # Format: {"issue_type_id": "workflow_id"}
    mappings = models.JSONField(
        _('mappings'),
        default=dict,
        blank=True,
        help_text=_('Issue type to workflow mappings')
    )

    is_active = models.BooleanField(
        _('is active'),
        default=True,
        db_index=True,
        help_text=_('Whether this scheme is active')
    )

    class Meta:
        db_table = 'workflow_schemes'
        verbose_name = _('workflow scheme')
        verbose_name_plural = _('workflow schemes')
        ordering = ['project', 'name']
        indexes = [
            models.Index(fields=['project', 'is_active']),
        ]

    def __str__(self):
        """String representation."""
        return f"{self.name} ({self.project.key})"

    def __repr__(self):
        """Developer-friendly representation."""
        return f"<WorkflowScheme name={self.name} project={self.project.key}>"

    def get_workflow_for_issue_type(self, issue_type):
        """
        Get the workflow for a specific issue type.

        Args:
            issue_type: IssueType instance or ID

        Returns:
            Workflow instance
        """
        issue_type_id = str(issue_type.id) if hasattr(issue_type, 'id') else str(issue_type)

        # Check if there's a specific mapping
        if issue_type_id in self.mappings:
            workflow_id = self.mappings[issue_type_id]
            try:
                return Workflow.objects.get(id=workflow_id)
            except Workflow.DoesNotExist:
                pass

        # Return default workflow
        return self.default_workflow

    def set_workflow_for_issue_type(self, issue_type, workflow):
        """
        Set the workflow for a specific issue type.

        Args:
            issue_type: IssueType instance or ID
            workflow: Workflow instance or ID
        """
        issue_type_id = str(issue_type.id) if hasattr(issue_type, 'id') else str(issue_type)
        workflow_id = str(workflow.id) if hasattr(workflow, 'id') else str(workflow)

        if not self.mappings:
            self.mappings = {}

        self.mappings[issue_type_id] = workflow_id
        self.save(update_fields=['mappings', 'updated_at'])

    def remove_workflow_for_issue_type(self, issue_type):
        """
        Remove the workflow mapping for a specific issue type.

        Args:
            issue_type: IssueType instance or ID
        """
        issue_type_id = str(issue_type.id) if hasattr(issue_type, 'id') else str(issue_type)

        if self.mappings and issue_type_id in self.mappings:
            del self.mappings[issue_type_id]
            self.save(update_fields=['mappings', 'updated_at'])
