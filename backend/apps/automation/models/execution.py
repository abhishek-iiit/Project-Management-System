"""
Automation execution tracking model.

Following CLAUDE.md best practices:
- Track all automation executions for audit trail
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.common.models import BaseModel


class ExecutionStatus(models.TextChoices):
    """Automation execution status."""
    SUCCESS = 'success', _('Success')
    FAILED = 'failed', _('Failed')
    PARTIAL = 'partial', _('Partial Success')


class AutomationExecutionQuerySet(models.QuerySet):
    """Custom queryset for AutomationExecution model."""

    def successful(self):
        """Filter successful executions."""
        return self.filter(status=ExecutionStatus.SUCCESS)

    def failed(self):
        """Filter failed executions."""
        return self.filter(status=ExecutionStatus.FAILED)

    def for_rule(self, rule):
        """Filter executions by rule."""
        return self.filter(rule=rule)

    def for_issue(self, issue):
        """Filter executions by issue."""
        return self.filter(issue=issue)

    def with_full_details(self):
        """Optimize query with all related data."""
        return self.select_related(
            'rule',
            'rule__organization',
            'rule__project',
            'issue',
            'issue__project'
        )


class AutomationExecution(BaseModel):
    """
    Automation execution record.

    Tracks each execution of an automation rule for audit trail.
    """

    rule = models.ForeignKey(
        'automation.AutomationRule',
        on_delete=models.CASCADE,
        related_name='executions',
        help_text=_('Automation rule that was executed')
    )

    issue = models.ForeignKey(
        'issues.Issue',
        on_delete=models.CASCADE,
        related_name='automation_executions',
        null=True,
        blank=True,
        help_text=_('Issue that triggered the automation (if applicable)')
    )

    # Trigger event data
    trigger_event = models.JSONField(
        _('trigger event'),
        default=dict,
        help_text=_('Event data that triggered this execution')
    )

    # Execution results
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=ExecutionStatus.choices,
        db_index=True,
        help_text=_('Execution status')
    )

    conditions_passed = models.BooleanField(
        _('conditions passed'),
        default=False,
        help_text=_('Whether all conditions passed')
    )

    conditions_result = models.JSONField(
        _('conditions result'),
        default=dict,
        blank=True,
        help_text=_('Result of each condition evaluation')
    )

    actions_executed = models.JSONField(
        _('actions executed'),
        default=list,
        blank=True,
        help_text=_('List of actions that were executed')
    )

    actions_result = models.JSONField(
        _('actions result'),
        default=dict,
        blank=True,
        help_text=_('Result of each action execution')
    )

    # Error information
    error_message = models.TextField(
        _('error message'),
        blank=True,
        help_text=_('Error message if execution failed')
    )

    error_details = models.JSONField(
        _('error details'),
        default=dict,
        blank=True,
        help_text=_('Detailed error information')
    )

    # Execution timing
    execution_time_ms = models.IntegerField(
        _('execution time (ms)'),
        null=True,
        blank=True,
        help_text=_('Execution time in milliseconds')
    )

    # Custom manager
    objects = AutomationExecutionQuerySet.as_manager()

    class Meta:
        db_table = 'automation_executions'
        verbose_name = _('automation execution')
        verbose_name_plural = _('automation executions')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['rule', '-created_at']),
            models.Index(fields=['issue', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        """String representation."""
        return f"{self.rule.name} - {self.status} ({self.created_at})"

    def __repr__(self):
        """Developer-friendly representation."""
        return f"<AutomationExecution rule={self.rule.name} status={self.status}>"

    def mark_success(self, conditions_result: dict, actions_result: dict, execution_time_ms: int):
        """
        Mark execution as successful.

        Args:
            conditions_result: Result of condition evaluations
            actions_result: Result of action executions
            execution_time_ms: Execution time in milliseconds
        """
        self.status = ExecutionStatus.SUCCESS
        self.conditions_passed = True
        self.conditions_result = conditions_result
        self.actions_result = actions_result
        self.execution_time_ms = execution_time_ms
        self.save()

    def mark_failed(self, error_message: str, error_details: dict = None, execution_time_ms: int = None):
        """
        Mark execution as failed.

        Args:
            error_message: Error message
            error_details: Detailed error information
            execution_time_ms: Execution time in milliseconds
        """
        self.status = ExecutionStatus.FAILED
        self.error_message = error_message
        self.error_details = error_details or {}
        self.execution_time_ms = execution_time_ms
        self.save()

    def mark_partial(
        self,
        conditions_result: dict,
        actions_result: dict,
        error_message: str,
        execution_time_ms: int
    ):
        """
        Mark execution as partially successful.

        Args:
            conditions_result: Result of condition evaluations
            actions_result: Result of action executions
            error_message: Error message for failed actions
            execution_time_ms: Execution time in milliseconds
        """
        self.status = ExecutionStatus.PARTIAL
        self.conditions_passed = True
        self.conditions_result = conditions_result
        self.actions_result = actions_result
        self.error_message = error_message
        self.execution_time_ms = execution_time_ms
        self.save()
