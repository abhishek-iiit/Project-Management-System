"""
Board views.

Following CLAUDE.md best practices:
- Thin views (orchestration only)
- Delegate to service layer
- Proper permissions
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse

from apps.boards.models import Board, Sprint, BoardType, SprintState
from apps.boards.services import BoardService, SprintService
from apps.boards.serializers import (
    BoardSerializer,
    BoardCreateSerializer,
    BoardIssueSerializer,
    SprintSerializer,
    SprintCreateSerializer,
    BoardStatisticsSerializer,
    SprintStatisticsSerializer,
    BurndownDataSerializer,
    AddIssueToBoardSerializer,
    RerankIssuesSerializer,
    AddIssueToSprintSerializer,
    BulkAddIssuesToSprintSerializer,
    MoveIssuesBetweenSprintsSerializer,
    CompleteSprintSerializer,
    ColumnConfigSerializer,
    SwimlaneConfigSerializer,
    QuickFiltersSerializer,
)
from apps.common.permissions import IsOrganizationMember


class BoardViewSet(viewsets.ModelViewSet):
    """
    ViewSet for boards.

    Endpoints:
    - GET /boards/ - List all boards
    - POST /boards/ - Create board
    - GET /boards/{id}/ - Get board
    - PUT /boards/{id}/ - Update board
    - PATCH /boards/{id}/ - Partial update board
    - DELETE /boards/{id}/ - Delete board
    - GET /boards/{id}/issues/ - Get board issues
    - POST /boards/{id}/add-issue/ - Add issue to board
    - POST /boards/{id}/remove-issue/ - Remove issue from board
    - POST /boards/{id}/rerank-issues/ - Rerank board issues
    - GET /boards/{id}/backlog/ - Get backlog issues
    - GET /boards/{id}/statistics/ - Get board statistics
    - POST /boards/{id}/update-columns/ - Update column config
    - POST /boards/{id}/update-swimlanes/ - Update swimlane config
    - POST /boards/{id}/update-filters/ - Update quick filters
    """

    permission_classes = [IsAuthenticated, IsOrganizationMember]
    serializer_class = BoardSerializer
    lookup_field = 'id'

    def get_queryset(self):
        """Get boards for current organization."""
        if not hasattr(self.request.user, 'current_organization'):
            return Board.objects.none()

        return Board.objects.filter(
            project__organization=self.request.user.current_organization
        ).with_full_details()

    def get_serializer_class(self):
        """Get appropriate serializer class."""
        if self.action == 'create':
            return BoardCreateSerializer
        return BoardSerializer

    @extend_schema(
        summary="List boards",
        parameters=[
            OpenApiParameter('project_id', str, description='Filter by project'),
            OpenApiParameter('board_type', str, description='Filter by board type'),
            OpenApiParameter('is_active', bool, description='Filter by active status'),
        ]
    )
    def list(self, request):
        """List boards with optional filters."""
        service = BoardService(user=request.user)

        # Get filter parameters
        project_id = request.query_params.get('project_id')
        board_type = request.query_params.get('board_type')
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            is_active = is_active.lower() == 'true'

        # Get boards
        boards = service.list_boards(
            project_id=project_id,
            board_type=board_type,
            is_active=is_active
        )

        serializer = self.get_serializer(boards, many=True)
        return Response({
            'status': 'success',
            'data': serializer.data
        })

    @extend_schema(summary="Create board")
    def create(self, request):
        """Create a new board."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = BoardService(user=request.user)
        board = service.create_board(serializer.validated_data)

        return Response({
            'status': 'success',
            'data': BoardSerializer(board).data,
            'message': 'Board created successfully'
        }, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Get board")
    def retrieve(self, request, id=None):
        """Get a specific board."""
        service = BoardService(user=request.user)
        board = service.get_board(id)

        serializer = self.get_serializer(board)
        return Response({
            'status': 'success',
            'data': serializer.data
        })

    @extend_schema(summary="Update board")
    def update(self, request, id=None):
        """Update a board."""
        service = BoardService(user=request.user)
        board = service.get_board(id)

        serializer = self.get_serializer(board, data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_board = service.update_board(id, serializer.validated_data)

        return Response({
            'status': 'success',
            'data': BoardSerializer(updated_board).data,
            'message': 'Board updated successfully'
        })

    @extend_schema(summary="Partially update board")
    def partial_update(self, request, id=None):
        """Partially update a board."""
        service = BoardService(user=request.user)
        board = service.get_board(id)

        serializer = self.get_serializer(board, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated_board = service.update_board(id, serializer.validated_data)

        return Response({
            'status': 'success',
            'data': BoardSerializer(updated_board).data,
            'message': 'Board updated successfully'
        })

    @extend_schema(summary="Delete board")
    def destroy(self, request, id=None):
        """Delete a board."""
        service = BoardService(user=request.user)
        service.delete_board(id)

        return Response({
            'status': 'success',
            'message': 'Board deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        summary="Get board issues",
        parameters=[
            OpenApiParameter('column', str, description='Filter by column name'),
            OpenApiParameter('quick_filter', str, description='Apply quick filter'),
        ]
    )
    @action(detail=True, methods=['get'])
    def issues(self, request, id=None):
        """Get issues on a board."""
        service = BoardService(user=request.user)

        column = request.query_params.get('column')
        quick_filter = request.query_params.get('quick_filter')

        issues = service.get_board_issues(id, column, quick_filter)

        from apps.issues.serializers import IssueSerializer
        serializer = IssueSerializer(issues, many=True)

        return Response({
            'status': 'success',
            'data': serializer.data
        })

    @extend_schema(
        summary="Add issue to board",
        request=AddIssueToBoardSerializer
    )
    @action(detail=True, methods=['post'])
    def add_issue(self, request, id=None):
        """Add an issue to a board."""
        serializer = AddIssueToBoardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = BoardService(user=request.user)
        board_issue = service.add_issue_to_board(
            id,
            serializer.validated_data['issue_id'],
            serializer.validated_data.get('rank')
        )

        return Response({
            'status': 'success',
            'data': BoardIssueSerializer(board_issue).data,
            'message': 'Issue added to board'
        }, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Remove issue from board",
        request=AddIssueToSprintSerializer
    )
    @action(detail=True, methods=['post'])
    def remove_issue(self, request, id=None):
        """Remove an issue from a board."""
        serializer = AddIssueToSprintSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = BoardService(user=request.user)
        service.remove_issue_from_board(id, serializer.validated_data['issue_id'])

        return Response({
            'status': 'success',
            'message': 'Issue removed from board'
        })

    @extend_schema(
        summary="Rerank board issues",
        request=RerankIssuesSerializer
    )
    @action(detail=True, methods=['post'])
    def rerank_issues(self, request, id=None):
        """Rerank issues on a board."""
        serializer = RerankIssuesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = BoardService(user=request.user)
        service.rerank_board_issues(id, serializer.validated_data['issue_order'])

        return Response({
            'status': 'success',
            'message': 'Issues reranked successfully'
        })

    @extend_schema(summary="Get backlog issues")
    @action(detail=True, methods=['get'])
    def backlog(self, request, id=None):
        """Get backlog issues for a board."""
        service = BoardService(user=request.user)
        issues = service.get_backlog_issues(id)

        from apps.issues.serializers import IssueSerializer
        serializer = IssueSerializer(issues, many=True)

        return Response({
            'status': 'success',
            'data': serializer.data
        })

    @extend_schema(
        summary="Get board statistics",
        responses={200: BoardStatisticsSerializer}
    )
    @action(detail=True, methods=['get'])
    def statistics(self, request, id=None):
        """Get board statistics."""
        service = BoardService(user=request.user)
        stats = service.get_board_statistics(id)

        return Response({
            'status': 'success',
            'data': stats
        })

    @extend_schema(
        summary="Update column configuration",
        request=ColumnConfigSerializer
    )
    @action(detail=True, methods=['post'])
    def update_columns(self, request, id=None):
        """Update board column configuration."""
        serializer = ColumnConfigSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = BoardService(user=request.user)
        board = service.update_column_config(id, serializer.validated_data)

        return Response({
            'status': 'success',
            'data': BoardSerializer(board).data,
            'message': 'Column configuration updated'
        })

    @extend_schema(
        summary="Update swimlane configuration",
        request=SwimlaneConfigSerializer
    )
    @action(detail=True, methods=['post'])
    def update_swimlanes(self, request, id=None):
        """Update board swimlane configuration."""
        serializer = SwimlaneConfigSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = BoardService(user=request.user)
        board = service.update_swimlane_config(id, serializer.validated_data)

        return Response({
            'status': 'success',
            'data': BoardSerializer(board).data,
            'message': 'Swimlane configuration updated'
        })

    @extend_schema(
        summary="Update quick filters",
        request=QuickFiltersSerializer
    )
    @action(detail=True, methods=['post'])
    def update_filters(self, request, id=None):
        """Update board quick filters."""
        serializer = QuickFiltersSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = BoardService(user=request.user)
        board = service.update_quick_filters(id, serializer.validated_data['quick_filters'])

        return Response({
            'status': 'success',
            'data': BoardSerializer(board).data,
            'message': 'Quick filters updated'
        })


class SprintViewSet(viewsets.ModelViewSet):
    """
    ViewSet for sprints.

    Endpoints:
    - GET /sprints/ - List all sprints
    - POST /sprints/ - Create sprint
    - GET /sprints/{id}/ - Get sprint
    - PUT /sprints/{id}/ - Update sprint
    - PATCH /sprints/{id}/ - Partial update sprint
    - DELETE /sprints/{id}/ - Delete sprint
    - POST /sprints/{id}/start/ - Start sprint
    - POST /sprints/{id}/complete/ - Complete sprint
    - GET /sprints/{id}/issues/ - Get sprint issues
    - POST /sprints/{id}/add-issue/ - Add issue to sprint
    - POST /sprints/{id}/remove-issue/ - Remove issue from sprint
    - POST /sprints/{id}/bulk-add-issues/ - Bulk add issues to sprint
    - GET /sprints/{id}/statistics/ - Get sprint statistics
    - GET /sprints/{id}/burndown/ - Get burndown chart data
    """

    permission_classes = [IsAuthenticated, IsOrganizationMember]
    serializer_class = SprintSerializer
    lookup_field = 'id'

    def get_queryset(self):
        """Get sprints for current organization."""
        if not hasattr(self.request.user, 'current_organization'):
            return Sprint.objects.none()

        return Sprint.objects.filter(
            board__project__organization=self.request.user.current_organization
        ).with_full_details()

    def get_serializer_class(self):
        """Get appropriate serializer class."""
        if self.action == 'create':
            return SprintCreateSerializer
        return SprintSerializer

    @extend_schema(
        summary="List sprints",
        parameters=[
            OpenApiParameter('board_id', str, description='Filter by board'),
            OpenApiParameter('state', str, description='Filter by state'),
        ]
    )
    def list(self, request):
        """List sprints with optional filters."""
        service = SprintService(user=request.user)

        # Get filter parameters
        board_id = request.query_params.get('board_id')
        state = request.query_params.get('state')

        # Get sprints
        sprints = service.list_sprints(
            board_id=board_id,
            state=state
        )

        serializer = self.get_serializer(sprints, many=True)
        return Response({
            'status': 'success',
            'data': serializer.data
        })

    @extend_schema(summary="Create sprint")
    def create(self, request):
        """Create a new sprint."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = SprintService(user=request.user)
        sprint = service.create_sprint(serializer.validated_data)

        return Response({
            'status': 'success',
            'data': SprintSerializer(sprint).data,
            'message': 'Sprint created successfully'
        }, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Get sprint")
    def retrieve(self, request, id=None):
        """Get a specific sprint."""
        service = SprintService(user=request.user)
        sprint = service.get_sprint(id)

        serializer = self.get_serializer(sprint)
        return Response({
            'status': 'success',
            'data': serializer.data
        })

    @extend_schema(summary="Update sprint")
    def update(self, request, id=None):
        """Update a sprint."""
        service = SprintService(user=request.user)
        sprint = service.get_sprint(id)

        serializer = self.get_serializer(sprint, data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_sprint = service.update_sprint(id, serializer.validated_data)

        return Response({
            'status': 'success',
            'data': SprintSerializer(updated_sprint).data,
            'message': 'Sprint updated successfully'
        })

    @extend_schema(summary="Partially update sprint")
    def partial_update(self, request, id=None):
        """Partially update a sprint."""
        service = SprintService(user=request.user)
        sprint = service.get_sprint(id)

        serializer = self.get_serializer(sprint, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated_sprint = service.update_sprint(id, serializer.validated_data)

        return Response({
            'status': 'success',
            'data': SprintSerializer(updated_sprint).data,
            'message': 'Sprint updated successfully'
        })

    @extend_schema(summary="Delete sprint")
    def destroy(self, request, id=None):
        """Delete a sprint."""
        service = SprintService(user=request.user)
        service.delete_sprint(id)

        return Response({
            'status': 'success',
            'message': 'Sprint deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary="Start sprint")
    @action(detail=True, methods=['post'])
    def start(self, request, id=None):
        """Start a sprint."""
        service = SprintService(user=request.user)
        sprint = service.start_sprint(id)

        return Response({
            'status': 'success',
            'data': SprintSerializer(sprint).data,
            'message': 'Sprint started successfully'
        })

    @extend_schema(
        summary="Complete sprint",
        request=CompleteSprintSerializer
    )
    @action(detail=True, methods=['post'])
    def complete(self, request, id=None):
        """Complete a sprint."""
        serializer = CompleteSprintSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = SprintService(user=request.user)
        sprint = service.complete_sprint(
            id,
            serializer.validated_data.get('move_incomplete_to')
        )

        return Response({
            'status': 'success',
            'data': SprintSerializer(sprint).data,
            'message': 'Sprint completed successfully'
        })

    @extend_schema(summary="Get sprint issues")
    @action(detail=True, methods=['get'])
    def issues(self, request, id=None):
        """Get issues in a sprint."""
        service = SprintService(user=request.user)
        issues = service.get_sprint_issues(id)

        from apps.issues.serializers import IssueSerializer
        serializer = IssueSerializer(issues, many=True)

        return Response({
            'status': 'success',
            'data': serializer.data
        })

    @extend_schema(
        summary="Add issue to sprint",
        request=AddIssueToSprintSerializer
    )
    @action(detail=True, methods=['post'])
    def add_issue(self, request, id=None):
        """Add an issue to a sprint."""
        serializer = AddIssueToSprintSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = SprintService(user=request.user)
        service.add_issue_to_sprint(id, serializer.validated_data['issue_id'])

        return Response({
            'status': 'success',
            'message': 'Issue added to sprint'
        }, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Remove issue from sprint",
        request=AddIssueToSprintSerializer
    )
    @action(detail=True, methods=['post'])
    def remove_issue(self, request, id=None):
        """Remove an issue from a sprint."""
        serializer = AddIssueToSprintSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = SprintService(user=request.user)
        service.remove_issue_from_sprint(id, serializer.validated_data['issue_id'])

        return Response({
            'status': 'success',
            'message': 'Issue removed from sprint'
        })

    @extend_schema(
        summary="Bulk add issues to sprint",
        request=BulkAddIssuesToSprintSerializer
    )
    @action(detail=True, methods=['post'])
    def bulk_add_issues(self, request, id=None):
        """Bulk add issues to a sprint."""
        serializer = BulkAddIssuesToSprintSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = SprintService(user=request.user)
        service.bulk_add_issues_to_sprint(id, serializer.validated_data['issue_ids'])

        return Response({
            'status': 'success',
            'message': f'Added {len(serializer.validated_data["issue_ids"])} issues to sprint'
        })

    @extend_schema(
        summary="Get sprint statistics",
        responses={200: SprintStatisticsSerializer}
    )
    @action(detail=True, methods=['get'])
    def statistics(self, request, id=None):
        """Get sprint statistics."""
        service = SprintService(user=request.user)
        stats = service.get_sprint_statistics(id)

        return Response({
            'status': 'success',
            'data': stats
        })

    @extend_schema(
        summary="Get burndown chart data",
        responses={200: BurndownDataSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def burndown(self, request, id=None):
        """Get burndown chart data for a sprint."""
        service = SprintService(user=request.user)
        burndown_data = service.get_sprint_burndown(id)

        return Response({
            'status': 'success',
            'data': burndown_data
        })
