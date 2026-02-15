"""
Sprint model for Scrum methodology.

Following CLAUDE.md best practices:
- Fat models with business logic
- State machine pattern for sprint lifecycle
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.common.models import BaseModel, AuditMixin
from decimal import Decimal


class SprintState(models.TextChoices):
    """Sprint states."""
    FUTURE = 'future', _('Future')
    ACTIVE = 'active', _('Active')
    CLOSED = 'closed', _('Closed')


class SprintQuerySet(models.QuerySet):
    """Custom queryset for Sprint model."""

    def active(self):
        """Filter active sprints."""
        return self.filter(state=SprintState.ACTIVE)

    def future(self):
        """Filter future sprints."""
        return self.filter(state=SprintState.FUTURE)

    def closed(self):
        """Filter closed sprints."""
        return self.filter(state=SprintState.CLOSED)

    def for_board(self, board):
        """Filter sprints by board."""
        return self.filter(board=board)

    def with_full_details(self):
        """Optimize query with all related data."""
        return self.select_related(
            'board',
            'board__project',
            'created_by',
            'updated_by'
        ).prefetch_related(
            'issues',
            'issues__status',
            'issues__assignee',
        )


class Sprint(BaseModel, AuditMixin):
    """
    Sprint for Scrum boards.

    Represents a time-boxed iteration with start/end dates and a goal.
    """

    board = models.ForeignKey(
        'boards.Board',
        on_delete=models.CASCADE,
        related_name='sprints',
        help_text=_('Board this sprint belongs to')
    )

    name = models.CharField(
        _('name'),
        max_length=100,
        help_text=_('Sprint name')
    )

    goal = models.TextField(
        _('goal'),
        blank=True,
        help_text=_('Sprint goal/objective')
    )

    # Dates
    start_date = models.DateTimeField(
        _('start date'),
        null=True,
        blank=True,
        help_text=_('Sprint start date')
    )

    end_date = models.DateTimeField(
        _('end date'),
        null=True,
        blank=True,
        help_text=_('Sprint end date')
    )

    completed_date = models.DateTimeField(
        _('completed date'),
        null=True,
        blank=True,
        help_text=_('Date when sprint was completed')
    )

    # State
    state = models.CharField(
        _('state'),
        max_length=20,
        choices=SprintState.choices,
        default=SprintState.FUTURE,
        db_index=True,
        help_text=_('Sprint state')
    )

    # Issues (M2M relationship)
    issues = models.ManyToManyField(
        'issues.Issue',
        related_name='sprints',
        blank=True,
        help_text=_('Issues in this sprint')
    )

    # Custom manager
    objects = SprintQuerySet.as_manager()

    class Meta:
        db_table = 'sprints'
        verbose_name = _('sprint')
        verbose_name_plural = _('sprints')
        ordering = ['board', '-start_date']
        unique_together = [['board', 'name']]
        indexes = [
            models.Index(fields=['board', 'state']),
            models.Index(fields=['board', '-start_date']),
            models.Index(fields=['state', 'start_date']),
        ]

    def __str__(self):
        """String representation."""
        return f"{self.name} ({self.board.name})"

    def __repr__(self):
        """Developer-friendly representation."""
        return f"<Sprint name={self.name} state={self.state} board={self.board.name}>"

    def clean(self):
        """Validate sprint."""
        super().clean()

        # Validate dates
        if self.start_date and self.end_date:
            if self.start_date >= self.end_date:
                raise ValidationError({
                    'end_date': _('End date must be after start date')
                })

        # Validate state transitions
        if self.pk:
            old_instance = Sprint.objects.get(pk=self.pk)

            # Cannot go from CLOSED back to ACTIVE or FUTURE
            if old_instance.state == SprintState.CLOSED and self.state != SprintState.CLOSED:
                raise ValidationError({
                    'state': _('Cannot reopen a closed sprint')
                })

            # Cannot go from ACTIVE to FUTURE
            if old_instance.state == SprintState.ACTIVE and self.state == SprintState.FUTURE:
                raise ValidationError({
                    'state': _('Cannot move active sprint back to future')
                })

    def start(self):
        """
        Start the sprint.

        Raises:
            ValidationError: If sprint cannot be started
        """
        if self.state != SprintState.FUTURE:
            raise ValidationError('Only future sprints can be started')

        # Check if board already has an active sprint
        active_sprint = self.board.sprints.filter(state=SprintState.ACTIVE).exclude(pk=self.pk).first()
        if active_sprint:
            raise ValidationError(f'Board already has an active sprint: {active_sprint.name}')

        # Set dates if not already set
        if not self.start_date:
            self.start_date = timezone.now()

        # Change state
        self.state = SprintState.ACTIVE
        self.save(update_fields=['state', 'start_date', 'updated_at'])

    def complete(self):
        """
        Complete the sprint.

        Moves incomplete issues to backlog or next sprint.

        Raises:
            ValidationError: If sprint cannot be completed
        """
        if self.state != SprintState.ACTIVE:
            raise ValidationError('Only active sprints can be completed')

        # Set completion date
        self.completed_date = timezone.now()
        self.state = SprintState.CLOSED
        self.save(update_fields=['state', 'completed_date', 'updated_at'])

    def add_issue(self, issue):
        """
        Add an issue to this sprint.

        Args:
            issue: Issue instance

        Raises:
            ValidationError: If sprint is closed
        """
        if self.state == SprintState.CLOSED:
            raise ValidationError('Cannot add issues to a closed sprint')

        self.issues.add(issue)

    def remove_issue(self, issue):
        """
        Remove an issue from this sprint.

        Args:
            issue: Issue instance
        """
        self.issues.remove(issue)

    def get_incomplete_issues(self):
        """
        Get incomplete issues in this sprint.

        Returns:
            QuerySet of Issue instances
        """
        # Get "Done" status category statuses
        done_statuses = self.board.project.organization.statuses.filter(
            category='done'
        )

        return self.issues.exclude(status__in=done_statuses)

    def get_completed_issues(self):
        """
        Get completed issues in this sprint.

        Returns:
            QuerySet of Issue instances
        """
        # Get "Done" status category statuses
        done_statuses = self.board.project.organization.statuses.filter(
            category='done'
        )

        return self.issues.filter(status__in=done_statuses)

    def calculate_completed_points(self):
        """
        Calculate total story points completed in this sprint.

        Returns:
            Decimal: Total story points
        """
        estimation_field = self.board.estimation_field or 'story_points'
        completed_issues = self.get_completed_issues()

        total_points = Decimal('0')
        for issue in completed_issues:
            # Get estimation from custom fields
            points = issue.custom_field_values.get(estimation_field, 0)
            if points:
                try:
                    total_points += Decimal(str(points))
                except (ValueError, TypeError):
                    pass

        return total_points

    def calculate_total_points(self):
        """
        Calculate total story points in this sprint.

        Returns:
            Decimal: Total story points
        """
        estimation_field = self.board.estimation_field or 'story_points'

        total_points = Decimal('0')
        for issue in self.issues.all():
            points = issue.custom_field_values.get(estimation_field, 0)
            if points:
                try:
                    total_points += Decimal(str(points))
                except (ValueError, TypeError):
                    pass

        return total_points

    def get_burndown_data(self):
        """
        Get burndown chart data for this sprint.

        Returns:
            List of dicts with date and remaining points
        """
        if not self.start_date or not self.end_date:
            return []

        # TODO: Implement detailed burndown tracking
        # This would require tracking issue completion dates
        # For now, return simple start/end points

        total_points = self.calculate_total_points()
        completed_points = self.calculate_completed_points()
        remaining_points = total_points - completed_points

        return [
            {
                'date': self.start_date.date(),
                'remaining': float(total_points),
                'ideal': float(total_points)
            },
            {
                'date': timezone.now().date() if self.state == SprintState.ACTIVE else self.end_date.date(),
                'remaining': float(remaining_points),
                'ideal': 0
            }
        ]

    def get_velocity(self):
        """
        Get velocity (completed points) for this sprint.

        Returns:
            float: Velocity
        """
        return float(self.calculate_completed_points())

    def get_progress_percentage(self):
        """
        Get completion progress as percentage.

        Returns:
            float: Progress percentage (0-100)
        """
        total_points = self.calculate_total_points()
        if total_points == 0:
            return 0.0

        completed_points = self.calculate_completed_points()
        return float((completed_points / total_points) * 100)

    def get_days_remaining(self):
        """
        Get number of days remaining in sprint.

        Returns:
            int: Days remaining (0 if sprint ended or not started)
        """
        if not self.end_date:
            return 0

        if self.state == SprintState.CLOSED:
            return 0

        if self.state == SprintState.FUTURE:
            return 0

        now = timezone.now()
        if now >= self.end_date:
            return 0

        delta = self.end_date - now
        return delta.days

    def get_duration_days(self):
        """
        Get sprint duration in days.

        Returns:
            int: Duration in days
        """
        if not self.start_date or not self.end_date:
            return 0

        delta = self.end_date - self.start_date
        return delta.days
