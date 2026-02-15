"""
Board service - business logic for boards.

Following CLAUDE.md best practices:
- Service layer for complex operations
- Transaction management
- Query optimization
"""

from typing import Dict, List, Optional
from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied
from django.contrib.auth import get_user_model
from apps.boards.models import Board, BoardIssue, BoardType
from apps.projects.models import Project
from apps.issues.models import Issue

User = get_user_model()


class BoardService:
    """Service for board operations."""

    def __init__(self, user: User):
        """
        Initialize board service.

        Args:
            user: User performing operations
        """
        self.user = user
        self.organization = getattr(user, 'current_organization', None)

    def _check_organization_permission(self):
        """Check if user has organization access."""
        if not self.organization:
            raise PermissionDenied("No organization context available")

    def _check_board_permission(self, board: Board):
        """Check if user can access board."""
        if board.project.organization_id != self.organization.id:
            raise PermissionDenied("Cannot access board from different organization")

    def _check_project_permission(self, project: Project):
        """Check if user can access project."""
        if project.organization_id != self.organization.id:
            raise PermissionDenied("Cannot access project from different organization")

    # ========================================
    # Board Operations
    # ========================================

    @transaction.atomic
    def create_board(self, data: Dict) -> Board:
        """
        Create a new board.

        Args:
            data: Board data

        Returns:
            Created Board instance

        Raises:
            PermissionDenied: If user lacks permissions
            ValidationError: If data is invalid
        """
        self._check_organization_permission()

        # Validate project
        project = data.get('project')
        if isinstance(project, str):
            project = Project.objects.get(id=project)
            data['project'] = project

        self._check_project_permission(project)

        # Set audit fields
        data['created_by'] = self.user
        data['updated_by'] = self.user

        # Create board
        board = Board(**data)
        board.full_clean()
        board.save()

        return board

    def get_board(self, board_id: str) -> Board:
        """
        Get a board by ID.

        Args:
            board_id: Board UUID

        Returns:
            Board instance

        Raises:
            PermissionDenied: If user lacks permissions
            Board.DoesNotExist: If board not found
        """
        self._check_organization_permission()

        board = Board.objects.with_full_details().get(id=board_id)
        self._check_board_permission(board)

        return board

    def list_boards(
        self,
        project_id: Optional[str] = None,
        board_type: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[Board]:
        """
        List boards for organization.

        Args:
            project_id: Filter by project
            board_type: Filter by board type
            is_active: Filter by active status

        Returns:
            List of Board instances
        """
        self._check_organization_permission()

        queryset = Board.objects.filter(
            project__organization=self.organization
        ).with_full_details()

        if project_id:
            queryset = queryset.filter(project_id=project_id)

        if board_type:
            queryset = queryset.filter(board_type=board_type)

        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        return list(queryset)

    @transaction.atomic
    def update_board(
        self,
        board_id: str,
        data: Dict
    ) -> Board:
        """
        Update a board.

        Args:
            board_id: Board UUID
            data: Update data

        Returns:
            Updated Board instance

        Raises:
            PermissionDenied: If user lacks permissions
            ValidationError: If data is invalid
        """
        board = self.get_board(board_id)

        # Update fields
        for key, value in data.items():
            if key not in ['id', 'project', 'created_by', 'created_at']:
                setattr(board, key, value)

        # Set audit fields
        board.updated_by = self.user

        # Validate and save
        board.full_clean()
        board.save()

        return board

    @transaction.atomic
    def delete_board(self, board_id: str) -> None:
        """
        Delete (soft delete) a board.

        Args:
            board_id: Board UUID

        Raises:
            PermissionDenied: If user lacks permissions
        """
        board = self.get_board(board_id)
        board.delete()  # Soft delete

    @transaction.atomic
    def update_column_config(
        self,
        board_id: str,
        column_config: Dict
    ) -> Board:
        """
        Update board column configuration.

        Args:
            board_id: Board UUID
            column_config: Column configuration

        Returns:
            Updated Board instance

        Raises:
            PermissionDenied: If user lacks permissions
            ValidationError: If config is invalid
        """
        board = self.get_board(board_id)

        board.column_config = column_config
        board.updated_by = self.user

        board.full_clean()
        board.save()

        return board

    @transaction.atomic
    def update_swimlane_config(
        self,
        board_id: str,
        swimlane_config: Dict
    ) -> Board:
        """
        Update board swimlane configuration.

        Args:
            board_id: Board UUID
            swimlane_config: Swimlane configuration

        Returns:
            Updated Board instance

        Raises:
            PermissionDenied: If user lacks permissions
            ValidationError: If config is invalid
        """
        board = self.get_board(board_id)

        board.swimlane_config = swimlane_config
        board.updated_by = self.user

        board.full_clean()
        board.save()

        return board

    @transaction.atomic
    def update_quick_filters(
        self,
        board_id: str,
        quick_filters: List[Dict]
    ) -> Board:
        """
        Update board quick filters.

        Args:
            board_id: Board UUID
            quick_filters: Quick filter definitions

        Returns:
            Updated Board instance

        Raises:
            PermissionDenied: If user lacks permissions
            ValidationError: If filters are invalid
        """
        board = self.get_board(board_id)

        board.quick_filters = quick_filters
        board.updated_by = self.user

        board.full_clean()
        board.save()

        return board

    # ========================================
    # Board Issue Operations
    # ========================================

    @transaction.atomic
    def add_issue_to_board(
        self,
        board_id: str,
        issue_id: str,
        rank: Optional[int] = None
    ) -> BoardIssue:
        """
        Add an issue to a board.

        Args:
            board_id: Board UUID
            issue_id: Issue UUID
            rank: Position on board (optional)

        Returns:
            BoardIssue instance

        Raises:
            PermissionDenied: If user lacks permissions
            ValidationError: If issue/board invalid
        """
        board = self.get_board(board_id)
        issue = Issue.objects.get(id=issue_id)

        # Validate issue belongs to same project
        if issue.project_id != board.project_id:
            raise ValidationError("Issue must belong to same project as board")

        board_issue = board.add_issue(issue, rank)
        return board_issue

    @transaction.atomic
    def remove_issue_from_board(
        self,
        board_id: str,
        issue_id: str
    ) -> None:
        """
        Remove an issue from a board.

        Args:
            board_id: Board UUID
            issue_id: Issue UUID

        Raises:
            PermissionDenied: If user lacks permissions
        """
        board = self.get_board(board_id)
        issue = Issue.objects.get(id=issue_id)

        board.remove_issue(issue)

    @transaction.atomic
    def rerank_board_issues(
        self,
        board_id: str,
        issue_order: List[str]
    ) -> None:
        """
        Rerank issues on a board.

        Args:
            board_id: Board UUID
            issue_order: List of issue IDs in desired order

        Raises:
            PermissionDenied: If user lacks permissions
            ValidationError: If issues invalid
        """
        board = self.get_board(board_id)

        # Validate all issues are on this board
        board_issue_ids = set(
            board.board_issues.values_list('issue_id', flat=True)
        )

        for issue_id in issue_order:
            if issue_id not in [str(bid) for bid in board_issue_ids]:
                raise ValidationError(f"Issue {issue_id} is not on this board")

        # Rerank
        board.rerank_issues(issue_order)

    def get_board_issues(
        self,
        board_id: str,
        column: Optional[str] = None,
        quick_filter: Optional[str] = None
    ) -> List[Issue]:
        """
        Get issues on a board.

        Args:
            board_id: Board UUID
            column: Filter by column name
            quick_filter: Apply quick filter

        Returns:
            List of Issue instances ordered by rank

        Raises:
            PermissionDenied: If user lacks permissions
        """
        board = self.get_board(board_id)

        # Get base queryset
        issues = Issue.objects.filter(
            board_issues__board=board
        ).select_related(
            'status', 'priority', 'assignee', 'reporter', 'issue_type'
        ).order_by('board_issues__rank')

        # Filter by column
        if column:
            column_config = next(
                (col for col in board.column_config.get('columns', []) if col.get('name') == column),
                None
            )
            if column_config:
                status_ids = column_config.get('status_ids', [])
                issues = issues.filter(status_id__in=status_ids)

        # Apply quick filter
        if quick_filter:
            # TODO: Implement JQL parsing and filtering
            # For now, simple filters
            if quick_filter == 'my_issues':
                issues = issues.filter(assignee=self.user)
            elif quick_filter == 'unassigned':
                issues = issues.filter(assignee__isnull=True)

        return list(issues)

    def get_issues_by_column(self, board_id: str) -> Dict[str, List[Issue]]:
        """
        Get board issues grouped by column.

        Args:
            board_id: Board UUID

        Returns:
            Dict mapping column names to issue lists

        Raises:
            PermissionDenied: If user lacks permissions
        """
        board = self.get_board(board_id)
        return board.get_issues_by_column()

    def get_backlog_issues(self, board_id: str) -> List[Issue]:
        """
        Get backlog issues for a board.

        Args:
            board_id: Board UUID

        Returns:
            List of Issue instances

        Raises:
            PermissionDenied: If user lacks permissions
        """
        board = self.get_board(board_id)
        return list(board.get_backlog_issues())

    # ========================================
    # Board Analytics
    # ========================================

    def get_board_velocity(
        self,
        board_id: str,
        sprint_count: int = 3
    ) -> float:
        """
        Get average velocity for a board.

        Args:
            board_id: Board UUID
            sprint_count: Number of sprints to consider

        Returns:
            Average velocity

        Raises:
            PermissionDenied: If user lacks permissions
        """
        board = self.get_board(board_id)
        return board.calculate_velocity(sprint_count)

    def get_board_statistics(self, board_id: str) -> Dict:
        """
        Get statistics for a board.

        Args:
            board_id: Board UUID

        Returns:
            Dict with board statistics

        Raises:
            PermissionDenied: If user lacks permissions
        """
        board = self.get_board(board_id)

        # Get issue counts by column
        issues_by_column = board.get_issues_by_column()
        column_counts = {
            column: len(issues)
            for column, issues in issues_by_column.items()
        }

        # Get total issues
        total_issues = board.board_issues.count()

        # Get backlog count
        backlog_count = board.get_backlog_issues().count()

        # Get active sprint (if Scrum)
        active_sprint = None
        if board.board_type == BoardType.SCRUM:
            sprint = board.get_active_sprint()
            if sprint:
                active_sprint = {
                    'id': str(sprint.id),
                    'name': sprint.name,
                    'days_remaining': sprint.get_days_remaining(),
                    'progress': sprint.get_progress_percentage()
                }

        # Get velocity (if Scrum)
        velocity = None
        if board.board_type == BoardType.SCRUM:
            velocity = board.calculate_velocity()

        return {
            'total_issues': total_issues,
            'backlog_count': backlog_count,
            'column_counts': column_counts,
            'active_sprint': active_sprint,
            'velocity': velocity
        }
