"""
Automation rule model.

Following CLAUDE.md best practices:
- Fat models with business logic
- JSONB for flexible configurations
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from apps.common.models import BaseModel, AuditMixin


class TriggerType(models.TextChoices):
    """Automation trigger types."""
    ISSUE_CREATED = 'issue_created', _('Issue Created')
    ISSUE_UPDATED = 'issue_updated', _('Issue Updated')
    FIELD_CHANGED = 'field_changed', _('Field Value Changed')
    ISSUE_TRANSITIONED = 'issue_transitioned', _('Issue Transitioned')
    ISSUE_ASSIGNED = 'issue_assigned', _('Issue Assigned')
    COMMENT_ADDED = 'comment_added', _('Comment Added')
    SCHEDULED = 'scheduled', _('Scheduled (Cron)')


class AutomationRuleQuerySet(models.QuerySet):
    """Custom queryset for AutomationRule model."""

    def active(self):
        """Filter active rules."""
        return self.filter(is_active=True)

    def for_organization(self, organization):
        """Filter rules by organization."""
        return self.filter(organization=organization)

    def for_project(self, project):
        """Filter rules by project."""
        return self.filter(
            models.Q(project=project) | models.Q(project__isnull=True),
            organization=project.organization
        )

    def by_trigger(self, trigger_type):
        """Filter rules by trigger type."""
        return self.filter(trigger_type=trigger_type)

    def with_full_details(self):
        """Optimize query with all related data."""
        return self.select_related(
            'organization',
            'project',
            'created_by',
            'updated_by'
        )


class AutomationRule(BaseModel, AuditMixin):
    """
    Automation rule.

    Defines trigger, conditions, and actions for automation.
    """

    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='automation_rules',
        help_text=_('Organization this rule belongs to')
    )

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='automation_rules',
        null=True,
        blank=True,
        help_text=_('Project this rule applies to (null for organization-wide)')
    )

    name = models.CharField(
        _('name'),
        max_length=200,
        help_text=_('Rule name')
    )

    description = models.TextField(
        _('description'),
        blank=True,
        help_text=_('Rule description')
    )

    # Trigger
    trigger_type = models.CharField(
        _('trigger type'),
        max_length=50,
        choices=TriggerType.choices,
        db_index=True,
        help_text=_('Type of trigger that activates this rule')
    )

    trigger_config = models.JSONField(
        _('trigger configuration'),
        default=dict,
        blank=True,
        help_text=_('Trigger-specific configuration (e.g., which field changed)')
    )

    # Conditions (list of condition objects)
    conditions = models.JSONField(
        _('conditions'),
        default=list,
        blank=True,
        help_text=_('List of conditions that must be met for rule to execute')
    )

    # Actions (list of action objects)
    actions = models.JSONField(
        _('actions'),
        default=list,
        blank=True,
        help_text=_('List of actions to execute when rule triggers and conditions pass')
    )

    # Status
    is_active = models.BooleanField(
        _('is active'),
        default=True,
        db_index=True,
        help_text=_('Whether this rule is active')
    )

    # Execution stats
    execution_count = models.IntegerField(
        _('execution count'),
        default=0,
        help_text=_('Number of times this rule has been executed')
    )

    last_executed_at = models.DateTimeField(
        _('last executed at'),
        null=True,
        blank=True,
        help_text=_('When this rule was last executed')
    )

    # Custom manager
    objects = AutomationRuleQuerySet.as_manager()

    class Meta:
        db_table = 'automation_rules'
        verbose_name = _('automation rule')
        verbose_name_plural = _('automation rules')
        ordering = ['organization', 'name']
        indexes = [
            models.Index(fields=['organization', 'is_active']),
            models.Index(fields=['project', 'is_active']),
            models.Index(fields=['trigger_type', 'is_active']),
            models.Index(fields=['organization', 'trigger_type']),
        ]

    def __str__(self):
        """String representation."""
        scope = f"({self.project.key})" if self.project else "(Org-wide)"
        return f"{self.name} {scope}"

    def __repr__(self):
        """Developer-friendly representation."""
        return f"<AutomationRule name={self.name} trigger={self.trigger_type}>"

    def clean(self):
        """Validate automation rule."""
        super().clean()

        # Validate trigger configuration
        if not isinstance(self.trigger_config, dict):
            raise ValidationError({
                'trigger_config': _('Trigger configuration must be a dictionary')
            })

        # Validate trigger-specific config
        if self.trigger_type == TriggerType.FIELD_CHANGED:
            if 'field' not in self.trigger_config:
                raise ValidationError({
                    'trigger_config': _('field_changed trigger must specify "field" in config')
                })

        elif self.trigger_type == TriggerType.SCHEDULED:
            if 'cron' not in self.trigger_config:
                raise ValidationError({
                    'trigger_config': _('scheduled trigger must specify "cron" expression in config')
                })

        # Validate conditions
        if not isinstance(self.conditions, list):
            raise ValidationError({
                'conditions': _('Conditions must be a list')
            })

        for idx, condition in enumerate(self.conditions):
            if not isinstance(condition, dict):
                raise ValidationError({
                    'conditions': f'Condition {idx} must be a dictionary'
                })
            if 'type' not in condition:
                raise ValidationError({
                    'conditions': f'Condition {idx} must have a "type"'
                })
            if 'config' not in condition:
                raise ValidationError({
                    'conditions': f'Condition {idx} must have a "config"'
                })

        # Validate actions
        if not isinstance(self.actions, list):
            raise ValidationError({
                'actions': _('Actions must be a list')
            })

        if not self.actions:
            raise ValidationError({
                'actions': _('At least one action is required')
            })

        for idx, action in enumerate(self.actions):
            if not isinstance(action, dict):
                raise ValidationError({
                    'actions': f'Action {idx} must be a dictionary'
                })
            if 'type' not in action:
                raise ValidationError({
                    'actions': f'Action {idx} must have a "type"'
                })
            if 'config' not in action:
                raise ValidationError({
                    'actions': f'Action {idx} must have a "config"'
                })

        # Validate project belongs to organization
        if self.project and self.project.organization_id != self.organization_id:
            raise ValidationError({
                'project': _('Project must belong to the same organization')
            })

    def should_execute_for_event(self, event_data: dict) -> bool:
        """
        Check if this rule should execute for the given event.

        Args:
            event_data: Event data dictionary

        Returns:
            Boolean indicating if rule should execute
        """
        # Check if rule is active
        if not self.is_active:
            return False

        # Check trigger type matches
        if event_data.get('trigger_type') != self.trigger_type:
            return False

        # Check project scope
        if self.project:
            issue_project_id = event_data.get('issue', {}).get('project_id')
            if str(self.project.id) != str(issue_project_id):
                return False

        # Check trigger-specific conditions
        if self.trigger_type == TriggerType.FIELD_CHANGED:
            field_name = self.trigger_config.get('field')
            changed_fields = event_data.get('changed_fields', [])
            if field_name not in changed_fields:
                return False

        return True

    def increment_execution_count(self):
        """Increment execution count."""
        from django.utils import timezone
        self.execution_count += 1
        self.last_executed_at = timezone.now()
        self.save(update_fields=['execution_count', 'last_executed_at', 'updated_at'])
