"""
Sprint service - business logic for sprints.

Following CLAUDE.md best practices:
- Service layer for complex operations
- Transaction management
- Query optimization
"""

from typing import Dict, List, Optional
from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied
from django.contrib.auth import get_user_model
from apps.boards.models import Sprint, SprintState, Board
from apps.issues.models import Issue

User = get_user_model()


class SprintService:
    """Service for sprint operations."""

    def __init__(self, user: User):
        """
        Initialize sprint service.

        Args:
            user: User performing operations
        """
        self.user = user
        self.organization = getattr(user, 'current_organization', None)

    def _check_organization_permission(self):
        """Check if user has organization access."""
        if not self.organization:
            raise PermissionDenied("No organization context available")

    def _check_sprint_permission(self, sprint: Sprint):
        """Check if user can access sprint."""
        if sprint.board.project.organization_id != self.organization.id:
            raise PermissionDenied("Cannot access sprint from different organization")

    def _check_board_permission(self, board: Board):
        """Check if user can access board."""
        if board.project.organization_id != self.organization.id:
            raise PermissionDenied("Cannot access board from different organization")

    # ========================================
    # Sprint Operations
    # ========================================

    @transaction.atomic
    def create_sprint(self, data: Dict) -> Sprint:
        """
        Create a new sprint.

        Args:
            data: Sprint data

        Returns:
            Created Sprint instance

        Raises:
            PermissionDenied: If user lacks permissions
            ValidationError: If data is invalid
        """
        self._check_organization_permission()

        # Validate board
        board = data.get('board')
        if isinstance(board, str):
            board = Board.objects.get(id=board)
            data['board'] = board

        self._check_board_permission(board)

        # Validate board is Scrum
        from apps.boards.models import BoardType
        if board.board_type != BoardType.SCRUM:
            raise ValidationError("Sprints can only be created for Scrum boards")

        # Set audit fields
        data['created_by'] = self.user
        data['updated_by'] = self.user

        # Create sprint
        sprint = Sprint(**data)
        sprint.full_clean()
        sprint.save()

        return sprint

    def get_sprint(self, sprint_id: str) -> Sprint:
        """
        Get a sprint by ID.

        Args:
            sprint_id: Sprint UUID

        Returns:
            Sprint instance

        Raises:
            PermissionDenied: If user lacks permissions
            Sprint.DoesNotExist: If sprint not found
        """
        self._check_organization_permission()

        sprint = Sprint.objects.with_full_details().get(id=sprint_id)
        self._check_sprint_permission(sprint)

        return sprint

    def list_sprints(
        self,
        board_id: Optional[str] = None,
        state: Optional[str] = None
    ) -> List[Sprint]:
        """
        List sprints.

        Args:
            board_id: Filter by board
            state: Filter by state

        Returns:
            List of Sprint instances
        """
        self._check_organization_permission()

        queryset = Sprint.objects.filter(
            board__project__organization=self.organization
        ).with_full_details()

        if board_id:
            queryset = queryset.filter(board_id=board_id)

        if state:
            queryset = queryset.filter(state=state)

        return list(queryset)

    @transaction.atomic
    def update_sprint(
        self,
        sprint_id: str,
        data: Dict
    ) -> Sprint:
        """
        Update a sprint.

        Args:
            sprint_id: Sprint UUID
            data: Update data

        Returns:
            Updated Sprint instance

        Raises:
            PermissionDenied: If user lacks permissions
            ValidationError: If data is invalid
        """
        sprint = self.get_sprint(sprint_id)

        # Update fields
        for key, value in data.items():
            if key not in ['id', 'board', 'created_by', 'created_at', 'issues']:
                setattr(sprint, key, value)

        # Set audit fields
        sprint.updated_by = self.user

        # Validate and save
        sprint.full_clean()
        sprint.save()

        return sprint

    @transaction.atomic
    def delete_sprint(self, sprint_id: str) -> None:
        """
        Delete (soft delete) a sprint.

        Args:
            sprint_id: Sprint UUID

        Raises:
            PermissionDenied: If user lacks permissions
            ValidationError: If sprint is active
        """
        sprint = self.get_sprint(sprint_id)

        # Cannot delete active sprint
        if sprint.state == SprintState.ACTIVE:
            raise ValidationError("Cannot delete an active sprint. Complete it first.")

        sprint.delete()  # Soft delete

    # ========================================
    # Sprint Lifecycle
    # ========================================

    @transaction.atomic
    def start_sprint(self, sprint_id: str) -> Sprint:
        """
        Start a sprint.

        Args:
            sprint_id: Sprint UUID

        Returns:
            Updated Sprint instance

        Raises:
            PermissionDenied: If user lacks permissions
            ValidationError: If sprint cannot be started
        """
        sprint = self.get_sprint(sprint_id)

        # Start sprint
        sprint.start()

        return sprint

    @transaction.atomic
    def complete_sprint(
        self,
        sprint_id: str,
        move_incomplete_to: Optional[str] = None
    ) -> Sprint:
        """
        Complete a sprint.

        Args:
            sprint_id: Sprint UUID
            move_incomplete_to: Sprint ID to move incomplete issues to (optional)

        Returns:
            Updated Sprint instance

        Raises:
            PermissionDenied: If user lacks permissions
            ValidationError: If sprint cannot be completed
        """
        sprint = self.get_sprint(sprint_id)

        # Get incomplete issues before completing
        incomplete_issues = list(sprint.get_incomplete_issues())

        # Complete sprint
        sprint.complete()

        # Move incomplete issues if target sprint specified
        if move_incomplete_to:
            target_sprint = self.get_sprint(move_incomplete_to)

            for issue in incomplete_issues:
                sprint.remove_issue(issue)
                target_sprint.add_issue(issue)

        return sprint

    # ========================================
    # Sprint Issue Operations
    # ========================================

    @transaction.atomic
    def add_issue_to_sprint(
        self,
        sprint_id: str,
        issue_id: str
    ) -> None:
        """
        Add an issue to a sprint.

        Args:
            sprint_id: Sprint UUID
            issue_id: Issue UUID

        Raises:
            PermissionDenied: If user lacks permissions
            ValidationError: If issue/sprint invalid
        """
        sprint = self.get_sprint(sprint_id)
        issue = Issue.objects.get(id=issue_id)

        # Validate issue belongs to same project
        if issue.project_id != sprint.board.project_id:
            raise ValidationError("Issue must belong to same project as sprint")

        sprint.add_issue(issue)

    @transaction.atomic
    def remove_issue_from_sprint(
        self,
        sprint_id: str,
        issue_id: str
    ) -> None:
        """
        Remove an issue from a sprint.

        Args:
            sprint_id: Sprint UUID
            issue_id: Issue UUID

        Raises:
            PermissionDenied: If user lacks permissions
        """
        sprint = self.get_sprint(sprint_id)
        issue = Issue.objects.get(id=issue_id)

        sprint.remove_issue(issue)

    @transaction.atomic
    def bulk_add_issues_to_sprint(
        self,
        sprint_id: str,
        issue_ids: List[str]
    ) -> None:
        """
        Bulk add issues to a sprint.

        Args:
            sprint_id: Sprint UUID
            issue_ids: List of issue UUIDs

        Raises:
            PermissionDenied: If user lacks permissions
            ValidationError: If issues invalid
        """
        sprint = self.get_sprint(sprint_id)

        # Get issues
        issues = Issue.objects.filter(id__in=issue_ids)

        # Validate all issues belong to same project
        for issue in issues:
            if issue.project_id != sprint.board.project_id:
                raise ValidationError(
                    f"Issue {issue.key} does not belong to same project as sprint"
                )

        # Add issues
        sprint.issues.add(*issues)

    @transaction.atomic
    def move_issues_between_sprints(
        self,
        source_sprint_id: str,
        target_sprint_id: str,
        issue_ids: List[str]
    ) -> None:
        """
        Move issues from one sprint to another.

        Args:
            source_sprint_id: Source sprint UUID
            target_sprint_id: Target sprint UUID
            issue_ids: List of issue UUIDs

        Raises:
            PermissionDenied: If user lacks permissions
            ValidationError: If sprints/issues invalid
        """
        source_sprint = self.get_sprint(source_sprint_id)
        target_sprint = self.get_sprint(target_sprint_id)

        # Validate sprints belong to same board
        if source_sprint.board_id != target_sprint.board_id:
            raise ValidationError("Sprints must belong to same board")

        # Get issues
        issues = Issue.objects.filter(id__in=issue_ids)

        # Move issues
        for issue in issues:
            source_sprint.remove_issue(issue)
            target_sprint.add_issue(issue)

    # ========================================
    # Sprint Analytics
    # ========================================

    def get_sprint_issues(self, sprint_id: str) -> List[Issue]:
        """
        Get issues in a sprint.

        Args:
            sprint_id: Sprint UUID

        Returns:
            List of Issue instances

        Raises:
            PermissionDenied: If user lacks permissions
        """
        sprint = self.get_sprint(sprint_id)

        issues = sprint.issues.select_related(
            'status', 'priority', 'assignee', 'reporter', 'issue_type'
        ).all()

        return list(issues)

    def get_sprint_statistics(self, sprint_id: str) -> Dict:
        """
        Get statistics for a sprint.

        Args:
            sprint_id: Sprint UUID

        Returns:
            Dict with sprint statistics

        Raises:
            PermissionDenied: If user lacks permissions
        """
        sprint = self.get_sprint(sprint_id)

        total_issues = sprint.issues.count()
        completed_issues = sprint.get_completed_issues().count()
        incomplete_issues = sprint.get_incomplete_issues().count()

        total_points = sprint.calculate_total_points()
        completed_points = sprint.calculate_completed_points()
        remaining_points = total_points - completed_points

        return {
            'total_issues': total_issues,
            'completed_issues': completed_issues,
            'incomplete_issues': incomplete_issues,
            'total_points': float(total_points),
            'completed_points': float(completed_points),
            'remaining_points': float(remaining_points),
            'progress_percentage': sprint.get_progress_percentage(),
            'velocity': sprint.get_velocity(),
            'days_remaining': sprint.get_days_remaining(),
            'duration_days': sprint.get_duration_days()
        }

    def get_sprint_burndown(self, sprint_id: str) -> List[Dict]:
        """
        Get burndown chart data for a sprint.

        Args:
            sprint_id: Sprint UUID

        Returns:
            List of dicts with burndown data

        Raises:
            PermissionDenied: If user lacks permissions
        """
        sprint = self.get_sprint(sprint_id)
        return sprint.get_burndown_data()

    def get_active_sprint_for_board(self, board_id: str) -> Optional[Sprint]:
        """
        Get the active sprint for a board.

        Args:
            board_id: Board UUID

        Returns:
            Sprint instance or None

        Raises:
            PermissionDenied: If user lacks permissions
        """
        self._check_organization_permission()

        board = Board.objects.get(id=board_id)
        self._check_board_permission(board)

        return board.get_active_sprint()

    def get_future_sprints_for_board(self, board_id: str) -> List[Sprint]:
        """
        Get future sprints for a board.

        Args:
            board_id: Board UUID

        Returns:
            List of Sprint instances

        Raises:
            PermissionDenied: If user lacks permissions
        """
        sprints = self.list_sprints(
            board_id=board_id,
            state=SprintState.FUTURE
        )

        return sprints

    def get_closed_sprints_for_board(
        self,
        board_id: str,
        limit: int = 10
    ) -> List[Sprint]:
        """
        Get closed sprints for a board.

        Args:
            board_id: Board UUID
            limit: Maximum number of sprints to return

        Returns:
            List of Sprint instances

        Raises:
            PermissionDenied: If user lacks permissions
        """
        self._check_organization_permission()

        sprints = Sprint.objects.filter(
            board_id=board_id,
            board__project__organization=self.organization,
            state=SprintState.CLOSED
        ).with_full_details().order_by('-completed_date')[:limit]

        return list(sprints)
