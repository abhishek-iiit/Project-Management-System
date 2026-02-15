"""
Board models for agile workflow.

Following CLAUDE.md best practices:
- Fat models with business logic
- JSONB for flexible configurations
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from apps.common.models import BaseModel, AuditMixin
import uuid


class BoardType(models.TextChoices):
    """Board types."""
    SCRUM = 'scrum', _('Scrum')
    KANBAN = 'kanban', _('Kanban')


class BoardQuerySet(models.QuerySet):
    """Custom queryset for Board model."""

    def active(self):
        """Filter active boards."""
        return self.filter(is_active=True)

    def for_project(self, project):
        """Filter boards by project."""
        return self.filter(project=project)

    def scrum_boards(self):
        """Filter scrum boards."""
        return self.filter(board_type=BoardType.SCRUM)

    def kanban_boards(self):
        """Filter kanban boards."""
        return self.filter(board_type=BoardType.KANBAN)

    def with_full_details(self):
        """Optimize query with all related data."""
        return self.select_related(
            'project',
            'project__organization',
            'created_by',
            'updated_by'
        ).prefetch_related(
            'sprints',
            'board_issues',
            'board_issues__issue',
        )


class Board(BaseModel, AuditMixin):
    """
    Agile board for project management.

    Supports both Scrum and Kanban methodologies.
    """

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='boards',
        help_text=_('Project this board belongs to')
    )

    name = models.CharField(
        _('name'),
        max_length=100,
        help_text=_('Board name')
    )

    description = models.TextField(
        _('description'),
        blank=True,
        help_text=_('Board description')
    )

    board_type = models.CharField(
        _('board type'),
        max_length=20,
        choices=BoardType.choices,
        default=BoardType.SCRUM,
        help_text=_('Type of board (Scrum or Kanban)')
    )

    # Board configuration (JSONB)
    column_config = models.JSONField(
        _('column configuration'),
        default=dict,
        blank=True,
        help_text=_('Column configuration (status to column mapping)')
    )

    swimlane_config = models.JSONField(
        _('swimlane configuration'),
        default=dict,
        blank=True,
        help_text=_('Swimlane configuration (grouping strategy)')
    )

    quick_filters = models.JSONField(
        _('quick filters'),
        default=list,
        blank=True,
        help_text=_('Quick filter definitions (JQL-like queries)')
    )

    # Filter (JQL-like query for board issues)
    filter_query = models.TextField(
        _('filter query'),
        blank=True,
        help_text=_('JQL-like query to filter issues on this board')
    )

    # Estimation statistic (for velocity calculations)
    estimation_field = models.CharField(
        _('estimation field'),
        max_length=100,
        blank=True,
        help_text=_('Field used for estimations (e.g., "story_points")')
    )

    # Status
    is_active = models.BooleanField(
        _('is active'),
        default=True,
        db_index=True,
        help_text=_('Whether this board is active')
    )

    # Custom manager
    objects = BoardQuerySet.as_manager()

    class Meta:
        db_table = 'boards'
        verbose_name = _('board')
        verbose_name_plural = _('boards')
        ordering = ['project', 'name']
        unique_together = [['project', 'name']]
        indexes = [
            models.Index(fields=['project', 'board_type']),
            models.Index(fields=['project', 'is_active']),
        ]

    def __str__(self):
        """String representation."""
        return f"{self.name} ({self.project.key})"

    def __repr__(self):
        """Developer-friendly representation."""
        return f"<Board name={self.name} type={self.board_type} project={self.project.key}>"

    def clean(self):
        """Validate board configuration."""
        super().clean()

        # Validate column configuration
        if self.column_config:
            if not isinstance(self.column_config, dict):
                raise ValidationError({
                    'column_config': _('Column configuration must be a dictionary')
                })

            # Validate columns structure
            columns = self.column_config.get('columns', [])
            if not isinstance(columns, list):
                raise ValidationError({
                    'column_config': _('columns must be a list')
                })

            for idx, column in enumerate(columns):
                if not isinstance(column, dict):
                    raise ValidationError({
                        'column_config': f'Column {idx} must be a dictionary'
                    })
                if 'name' not in column or 'status_ids' not in column:
                    raise ValidationError({
                        'column_config': f'Column {idx} must have "name" and "status_ids"'
                    })

        # Validate swimlane configuration
        if self.swimlane_config:
            if not isinstance(self.swimlane_config, dict):
                raise ValidationError({
                    'swimlane_config': _('Swimlane configuration must be a dictionary')
                })

            swimlane_type = self.swimlane_config.get('type')
            if swimlane_type and swimlane_type not in ['assignee', 'priority', 'epic', 'issue_type', 'none']:
                raise ValidationError({
                    'swimlane_config': f'Invalid swimlane type: {swimlane_type}'
                })

        # Validate quick filters
        if self.quick_filters:
            if not isinstance(self.quick_filters, list):
                raise ValidationError({
                    'quick_filters': _('Quick filters must be a list')
                })

            for idx, filter_def in enumerate(self.quick_filters):
                if not isinstance(filter_def, dict):
                    raise ValidationError({
                        'quick_filters': f'Filter {idx} must be a dictionary'
                    })
                if 'name' not in filter_def:
                    raise ValidationError({
                        'quick_filters': f'Filter {idx} must have a "name"'
                    })

    def get_active_sprint(self):
        """
        Get the active sprint for this board (Scrum only).

        Returns:
            Sprint or None
        """
        if self.board_type != BoardType.SCRUM:
            return None

        from apps.boards.models.sprint import Sprint, SprintState
        return self.sprints.filter(state=SprintState.ACTIVE).first()

    def get_backlog_issues(self):
        """
        Get backlog issues (issues not in any sprint).

        Returns:
            QuerySet of Issue instances
        """
        from apps.issues.models import Issue

        # Get issue IDs on this board
        board_issue_ids = self.board_issues.values_list('issue_id', flat=True)

        # Get issues not in any active sprint
        backlog_issues = Issue.objects.filter(
            id__in=board_issue_ids
        ).exclude(
            sprints__state__in=['active', 'future']
        )

        return backlog_issues

    def add_issue(self, issue, rank=None):
        """
        Add an issue to this board.

        Args:
            issue: Issue instance
            rank: Position on the board (optional)

        Returns:
            BoardIssue instance
        """
        # Get max rank if not provided
        if rank is None:
            max_rank = self.board_issues.aggregate(
                models.Max('rank')
            )['rank__max'] or 0
            rank = max_rank + 1

        board_issue, created = BoardIssue.objects.get_or_create(
            board=self,
            issue=issue,
            defaults={'rank': rank}
        )

        if not created:
            board_issue.rank = rank
            board_issue.save(update_fields=['rank'])

        return board_issue

    def remove_issue(self, issue):
        """
        Remove an issue from this board.

        Args:
            issue: Issue instance
        """
        BoardIssue.objects.filter(board=self, issue=issue).delete()

    def rerank_issues(self, issue_order):
        """
        Rerank issues on the board.

        Args:
            issue_order: List of issue IDs in desired order
        """
        for rank, issue_id in enumerate(issue_order):
            BoardIssue.objects.filter(
                board=self,
                issue_id=issue_id
            ).update(rank=rank)

    def get_column_for_status(self, status):
        """
        Get column name for a given status.

        Args:
            status: Status instance or ID

        Returns:
            Column name or None
        """
        status_id = str(status.id) if hasattr(status, 'id') else str(status)

        columns = self.column_config.get('columns', [])
        for column in columns:
            if status_id in column.get('status_ids', []):
                return column.get('name')

        return None

    def get_issues_by_column(self):
        """
        Get issues grouped by column.

        Returns:
            Dict mapping column names to issue lists
        """
        from apps.issues.models import Issue

        result = {}
        columns = self.column_config.get('columns', [])

        for column in columns:
            column_name = column.get('name')
            status_ids = column.get('status_ids', [])

            # Get issues in this column
            issues = Issue.objects.filter(
                board_issues__board=self,
                status_id__in=status_ids
            ).select_related('status', 'assignee', 'priority').order_by('board_issues__rank')

            result[column_name] = list(issues)

        return result

    def calculate_velocity(self, sprint_count=3):
        """
        Calculate average velocity based on recent completed sprints.

        Args:
            sprint_count: Number of sprints to consider

        Returns:
            Average velocity (float)
        """
        from apps.boards.models.sprint import Sprint, SprintState

        # Get recent completed sprints
        completed_sprints = self.sprints.filter(
            state=SprintState.CLOSED
        ).order_by('-end_date')[:sprint_count]

        if not completed_sprints:
            return 0.0

        total_velocity = sum(
            sprint.calculate_completed_points()
            for sprint in completed_sprints
        )

        return total_velocity / len(completed_sprints)


class BoardIssue(BaseModel):
    """
    Many-to-many relationship between boards and issues with ranking.
    """

    board = models.ForeignKey(
        Board,
        on_delete=models.CASCADE,
        related_name='board_issues',
        help_text=_('Board')
    )

    issue = models.ForeignKey(
        'issues.Issue',
        on_delete=models.CASCADE,
        related_name='board_issues',
        help_text=_('Issue')
    )

    rank = models.IntegerField(
        _('rank'),
        default=0,
        db_index=True,
        help_text=_('Issue rank/position on the board (for ordering)')
    )

    class Meta:
        db_table = 'board_issues'
        verbose_name = _('board issue')
        verbose_name_plural = _('board issues')
        unique_together = [['board', 'issue']]
        ordering = ['board', 'rank']
        indexes = [
            models.Index(fields=['board', 'rank']),
            models.Index(fields=['issue']),
        ]

    def __str__(self):
        """String representation."""
        return f"{self.issue.key} on {self.board.name}"

    def __repr__(self):
        """Developer-friendly representation."""
        return f"<BoardIssue board={self.board.name} issue={self.issue.key} rank={self.rank}>"
