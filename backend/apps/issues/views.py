"""
Issue views for API endpoints.

Following CLAUDE.md best practices:
- Thin views (orchestration only)
- Business logic delegated to services
- Optimized queries
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from apps.issues.models import (
    Issue, IssueType, Priority, Label, Comment, Attachment,
    IssueLink, IssueLinkType
)
from apps.issues.serializers import (
    IssueSerializer,
    IssueMinimalSerializer,
    IssueCreateSerializer,
    IssueUpdateSerializer,
    TransitionIssueSerializer,
    IssueTypeSerializer,
    PrioritySerializer,
    LabelSerializer,
    CommentSerializer,
    AttachmentSerializer,
    IssueLinkSerializer,
    IssueLinkTypeSerializer,
    AddLinkSerializer,
    AddWatcherSerializer,
    LogWorkSerializer,
)
from apps.issues.services import IssueService, CommentService
from apps.workflows.models import Transition


class IssueViewSet(viewsets.ModelViewSet):
    """
    Issue management endpoints.

    Provides CRUD operations for issues with advanced features.
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project', 'status', 'issue_type', 'priority', 'assignee', 'reporter']
    search_fields = ['key', 'summary', 'description']
    ordering_fields = ['created_at', 'updated_at', 'due_date', 'priority__level']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return IssueCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return IssueUpdateSerializer
        elif self.action == 'list':
            return IssueMinimalSerializer
        return IssueSerializer

    def get_queryset(self):
        """Get optimized queryset with proper filtering."""
        # Base queryset with optimizations
        queryset = Issue.objects.with_full_details()

        # Filter by organization (from header)
        organization_id = self.request.headers.get('X-Organization-ID')
        if organization_id:
            queryset = queryset.for_organization(organization_id)

        # Filter by project (query param)
        project_id = self.request.query_params.get('project')
        if project_id:
            queryset = queryset.for_project(project_id)

        # Filter by status category
        status_category = self.request.query_params.get('status_category')
        if status_category:
            queryset = queryset.filter(status__category=status_category)

        # Filter by epic
        epic_id = self.request.query_params.get('epic')
        if epic_id:
            queryset = queryset.filter(epic_id=epic_id)

        # Filter by parent
        parent_id = self.request.query_params.get('parent')
        if parent_id:
            queryset = queryset.filter(parent_id=parent_id)

        # Filter open/closed
        is_open = self.request.query_params.get('is_open')
        if is_open is not None:
            if is_open.lower() == 'true':
                queryset = queryset.open_issues()
            else:
                queryset = queryset.closed_issues()

        return queryset

    def create(self, request):
        """Create a new issue."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Delegate to service
        service = IssueService(user=request.user)
        issue = service.create_issue(
            project=serializer.validated_data['project'],
            data=serializer.validated_data
        )

        return Response(
            IssueSerializer(issue).data,
            status=status.HTTP_201_CREATED
        )

    def update(self, request, pk=None):
        """Update issue details."""
        issue = self.get_object()
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Delegate to service
        service = IssueService(user=request.user)
        updated_issue = service.update_issue(
            issue=issue,
            data=serializer.validated_data
        )

        return Response(IssueSerializer(updated_issue).data)

    def destroy(self, request, pk=None):
        """Soft delete issue."""
        issue = self.get_object()

        # Delegate to service
        service = IssueService(user=request.user)
        service.delete_issue(issue)

        return Response(
            {
                'status': 'success',
                'message': 'Issue deleted successfully'
            },
            status=status.HTTP_204_NO_CONTENT
        )

    @action(detail=True, methods=['post'])
    def transition(self, request, pk=None):
        """Transition issue to a new status."""
        issue = self.get_object()

        serializer = TransitionIssueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get transition
        transition = get_object_or_404(
            Transition,
            id=serializer.validated_data['transition_id']
        )

        # Prepare data
        data = serializer.validated_data.get('additional_data', {})
        if 'resolution' in serializer.validated_data:
            data['resolution'] = serializer.validated_data['resolution']

        # Delegate to service
        service = IssueService(user=request.user)
        updated_issue = service.transition_issue(
            issue=issue,
            transition=transition,
            comment=serializer.validated_data.get('comment'),
            data=data
        )

        return Response(
            {
                'status': 'success',
                'data': IssueSerializer(updated_issue).data,
                'message': f'Issue transitioned to {updated_issue.status.name}'
            }
        )

    @action(detail=True, methods=['get'])
    def comments(self, request, pk=None):
        """Get issue comments."""
        issue = self.get_object()

        comments = issue.comments.select_related('user').order_by('created_at')
        serializer = CommentSerializer(comments, many=True)

        return Response({
            'status': 'success',
            'data': serializer.data
        })

    @action(detail=True, methods=['post'])
    def add_comment(self, request, pk=None):
        """Add a comment to issue."""
        issue = self.get_object()

        serializer = CommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Delegate to service
        service = CommentService(user=request.user)
        comment = service.create_comment(
            issue=issue,
            data=serializer.validated_data
        )

        return Response(
            {
                'status': 'success',
                'data': CommentSerializer(comment).data,
                'message': 'Comment added successfully'
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['get'])
    def attachments(self, request, pk=None):
        """Get issue attachments."""
        issue = self.get_object()

        attachments = issue.attachments.select_related('created_by').order_by('-created_at')
        serializer = AttachmentSerializer(attachments, many=True, context={'request': request})

        return Response({
            'status': 'success',
            'data': serializer.data
        })

    @action(detail=True, methods=['post'])
    def add_link(self, request, pk=None):
        """Add a link to another issue."""
        issue = self.get_object()

        serializer = AddLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get referenced objects
        to_issue = get_object_or_404(Issue, id=serializer.validated_data['to_issue_id'])
        link_type = get_object_or_404(IssueLinkType, id=serializer.validated_data['link_type_id'])

        # Delegate to service
        service = IssueService(user=request.user)
        link = service.add_link(
            from_issue=issue,
            to_issue=to_issue,
            link_type=link_type
        )

        return Response(
            {
                'status': 'success',
                'data': IssueLinkSerializer(link).data,
                'message': 'Issue link added successfully'
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['get'])
    def links(self, request, pk=None):
        """Get issue links."""
        issue = self.get_object()

        # Get both outward and inward links
        outward_links = issue.outward_links.select_related(
            'to_issue', 'link_type'
        )
        inward_links = issue.inward_links.select_related(
            'from_issue', 'link_type'
        )

        return Response({
            'status': 'success',
            'data': {
                'outward': IssueLinkSerializer(outward_links, many=True).data,
                'inward': IssueLinkSerializer(inward_links, many=True).data
            }
        })

    @action(detail=True, methods=['post'])
    def add_watcher(self, request, pk=None):
        """Add a watcher to issue."""
        issue = self.get_object()

        serializer = AddWatcherSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = get_object_or_404(User, id=serializer.validated_data['user_id'])

        # Delegate to service
        service = IssueService(user=request.user)
        service.add_watcher(issue, user)

        return Response(
            {
                'status': 'success',
                'message': 'Watcher added successfully'
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['delete'], url_path='watchers/(?P<user_id>[^/.]+)')
    def remove_watcher(self, request, pk=None, user_id=None):
        """Remove a watcher from issue."""
        issue = self.get_object()
        user = get_object_or_404(User, id=user_id)

        # Delegate to service
        service = IssueService(user=request.user)
        service.remove_watcher(issue, user)

        return Response(
            {
                'status': 'success',
                'message': 'Watcher removed successfully'
            }
        )

    @action(detail=True, methods=['post'])
    def log_work(self, request, pk=None):
        """Log work time on issue."""
        issue = self.get_object()

        serializer = LogWorkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Delegate to service
        service = IssueService(user=request.user)
        updated_issue = service.log_work(
            issue=issue,
            time_spent=serializer.validated_data['time_spent'],
            comment=serializer.validated_data.get('comment')
        )

        return Response(
            {
                'status': 'success',
                'data': {
                    'time_spent': updated_issue.time_spent,
                    'remaining_estimate': updated_issue.remaining_estimate
                },
                'message': 'Work logged successfully'
            }
        )

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get issue statistics."""
        issue = self.get_object()

        # Delegate to service
        service = IssueService(user=request.user)
        stats = service.get_issue_stats(issue)

        return Response({
            'status': 'success',
            'data': stats
        })

    @action(detail=True, methods=['get'])
    def subtasks(self, request, pk=None):
        """Get issue subtasks."""
        issue = self.get_object()

        subtasks = issue.get_subtasks().with_full_details()
        serializer = IssueMinimalSerializer(subtasks, many=True)

        return Response({
            'status': 'success',
            'data': serializer.data
        })


class IssueTypeViewSet(viewsets.ModelViewSet):
    """Issue type management endpoints."""

    serializer_class = IssueTypeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get issue types for user's organization."""
        organization_id = self.request.headers.get('X-Organization-ID')

        if not organization_id:
            return IssueType.objects.none()

        return IssueType.objects.filter(
            organization_id=organization_id,
            is_active=True
        ).order_by('position', 'name')


class PriorityViewSet(viewsets.ModelViewSet):
    """Priority management endpoints."""

    serializer_class = PrioritySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get priorities for user's organization."""
        organization_id = self.request.headers.get('X-Organization-ID')

        if not organization_id:
            return Priority.objects.none()

        return Priority.objects.filter(
            organization_id=organization_id,
            is_active=True
        ).order_by('level', 'name')


class LabelViewSet(viewsets.ModelViewSet):
    """Label management endpoints."""

    serializer_class = LabelSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get labels for user's organization."""
        organization_id = self.request.headers.get('X-Organization-ID')

        if not organization_id:
            return Label.objects.none()

        queryset = Label.objects.filter(organization_id=organization_id)

        # Filter by project if specified
        project_id = self.request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(
                models.Q(project_id=project_id) | models.Q(project__isnull=True)
            )

        return queryset.order_by('name')


class CommentViewSet(viewsets.ModelViewSet):
    """Comment management endpoints."""

    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get comments for accessible issues."""
        # Get user's projects
        from apps.projects.models import ProjectMember

        project_ids = ProjectMember.objects.filter(
            user=self.request.user,
            is_active=True
        ).values_list('project_id', flat=True)

        return Comment.objects.filter(
            issue__project_id__in=project_ids
        ).select_related('issue', 'user').order_by('-created_at')

    def update(self, request, pk=None):
        """Update comment."""
        comment = self.get_object()

        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Delegate to service
        service = CommentService(user=request.user)
        updated_comment = service.update_comment(
            comment=comment,
            data=serializer.validated_data
        )

        return Response(
            {
                'status': 'success',
                'data': self.get_serializer(updated_comment).data,
                'message': 'Comment updated successfully'
            }
        )

    def destroy(self, request, pk=None):
        """Delete comment."""
        comment = self.get_object()

        # Delegate to service
        service = CommentService(user=request.user)
        service.delete_comment(comment)

        return Response(
            {
                'status': 'success',
                'message': 'Comment deleted successfully'
            },
            status=status.HTTP_204_NO_CONTENT
        )


class IssueLinkTypeViewSet(viewsets.ModelViewSet):
    """Issue link type management endpoints."""

    serializer_class = IssueLinkTypeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get link types for user's organization."""
        organization_id = self.request.headers.get('X-Organization-ID')

        if not organization_id:
            return IssueLinkType.objects.none()

        return IssueLinkType.objects.filter(
            organization_id=organization_id,
            is_active=True
        ).order_by('name')
