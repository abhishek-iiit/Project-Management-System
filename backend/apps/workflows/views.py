"""
Workflow views for API endpoints.

Following CLAUDE.md best practices:
- Thin views (orchestration only)
- Business logic delegated to services
- Optimized queries with select_related/prefetch_related
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from apps.workflows.models import Workflow, Status, Transition, WorkflowScheme
from apps.workflows.serializers import (
    WorkflowSerializer,
    WorkflowMinimalSerializer,
    WorkflowCreateSerializer,
    StatusSerializer,
    TransitionSerializer,
    TransitionMinimalSerializer,
    WorkflowSchemeSerializer,
    WorkflowSchemeCreateSerializer,
    CloneWorkflowSerializer,
)
from apps.workflows.services import WorkflowEngine, TransitionService


class WorkflowViewSet(viewsets.ModelViewSet):
    """
    Workflow management endpoints.

    Provides CRUD operations for workflows with status and transition management.
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return WorkflowCreateSerializer
        elif self.action == 'list':
            return WorkflowMinimalSerializer
        return WorkflowSerializer

    def get_queryset(self):
        """
        Get optimized queryset with proper filtering.

        Uses .with_full_details() for optimal query performance.
        """
        # Get organization from header
        organization_id = self.request.headers.get('X-Organization-ID')

        if not organization_id:
            return Workflow.objects.none()

        # Base queryset with optimizations
        queryset = Workflow.objects.with_full_details()

        # Filter by organization
        queryset = queryset.for_organization(organization_id)

        # Query params filtering
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        is_default = self.request.query_params.get('is_default')
        if is_default is not None:
            queryset = queryset.filter(is_default=is_default.lower() == 'true')

        return queryset

    def create(self, request):
        """Create a new workflow."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create workflow
        workflow = Workflow.objects.create(
            created_by=request.user,
            **serializer.validated_data
        )

        return Response(
            WorkflowSerializer(workflow).data,
            status=status.HTTP_201_CREATED
        )

    def update(self, request, pk=None):
        """Update workflow details."""
        workflow = self.get_object()
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Update workflow
        for field, value in serializer.validated_data.items():
            setattr(workflow, field, value)

        workflow.updated_by = request.user
        workflow.save()

        return Response(WorkflowSerializer(workflow).data)

    def destroy(self, request, pk=None):
        """Soft delete workflow."""
        workflow = self.get_object()

        # Check if workflow is in use
        if WorkflowScheme.objects.filter(default_workflow=workflow).exists():
            return Response(
                {
                    'status': 'error',
                    'error': {
                        'code': 'WORKFLOW_IN_USE',
                        'message': 'Cannot delete workflow that is in use by projects'
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Soft delete
        workflow.delete()

        return Response(
            {
                'status': 'success',
                'message': 'Workflow deleted successfully'
            },
            status=status.HTTP_204_NO_CONTENT
        )

    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        """Clone workflow with all statuses and transitions."""
        workflow = self.get_object()

        serializer = CloneWorkflowSerializer(
            data=request.data,
            context={'workflow': workflow, 'request': request}
        )
        serializer.is_valid(raise_exception=True)

        # Clone workflow
        new_workflow = workflow.clone(
            new_name=serializer.validated_data['new_name'],
            organization=serializer.validated_data.get('organization')
        )

        return Response(
            {
                'status': 'success',
                'data': WorkflowSerializer(new_workflow).data,
                'message': 'Workflow cloned successfully'
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['get'])
    def statuses(self, request, pk=None):
        """Get workflow statuses."""
        workflow = self.get_object()

        statuses = workflow.statuses.filter(is_active=True).order_by('position', 'name')
        serializer = StatusSerializer(statuses, many=True)

        return Response({
            'status': 'success',
            'data': serializer.data
        })

    @action(detail=True, methods=['get'])
    def transitions(self, request, pk=None):
        """Get workflow transitions."""
        workflow = self.get_object()

        transitions = workflow.transitions.filter(
            is_active=True
        ).select_related('from_status', 'to_status').order_by('position', 'name')

        serializer = TransitionSerializer(transitions, many=True)

        return Response({
            'status': 'success',
            'data': serializer.data
        })


class StatusViewSet(viewsets.ModelViewSet):
    """
    Status management endpoints.

    Provides CRUD operations for workflow statuses.
    """

    serializer_class = StatusSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get statuses for user's current organization."""
        organization_id = self.request.headers.get('X-Organization-ID')

        if not organization_id:
            return Status.objects.none()

        return Status.objects.filter(
            workflow__organization_id=organization_id
        ).select_related('workflow', 'created_by', 'updated_by').order_by('workflow', 'position')

    def create(self, request):
        """Create a new status."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create status
        status_obj = Status.objects.create(
            created_by=request.user,
            **serializer.validated_data
        )

        return Response(
            {
                'status': 'success',
                'data': self.get_serializer(status_obj).data,
                'message': 'Status created successfully'
            },
            status=status.HTTP_201_CREATED
        )

    def update(self, request, pk=None):
        """Update status details."""
        status_obj = self.get_object()
        serializer = self.get_serializer(status_obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Update status
        for field, value in serializer.validated_data.items():
            setattr(status_obj, field, value)

        status_obj.updated_by = request.user
        status_obj.save()

        return Response(
            {
                'status': 'success',
                'data': self.get_serializer(status_obj).data,
                'message': 'Status updated successfully'
            }
        )

    def destroy(self, request, pk=None):
        """Delete status."""
        status_obj = self.get_object()

        # Check if status is in use
        # TODO: Check if issues exist with this status (Phase 5)

        # Check if this is the only status in workflow
        if status_obj.workflow.statuses.filter(is_active=True).count() <= 1:
            return Response(
                {
                    'status': 'error',
                    'error': {
                        'code': 'LAST_STATUS',
                        'message': 'Cannot delete the last status in a workflow'
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Soft delete
        status_obj.delete()

        return Response(
            {
                'status': 'success',
                'message': 'Status deleted successfully'
            },
            status=status.HTTP_204_NO_CONTENT
        )


class TransitionViewSet(viewsets.ModelViewSet):
    """
    Transition management endpoints.

    Provides CRUD operations for workflow transitions.
    """

    serializer_class = TransitionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get transitions for user's current organization."""
        organization_id = self.request.headers.get('X-Organization-ID')

        if not organization_id:
            return Transition.objects.none()

        return Transition.objects.filter(
            workflow__organization_id=organization_id
        ).select_related(
            'workflow', 'from_status', 'to_status', 'created_by', 'updated_by'
        ).order_by('workflow', 'position')

    def create(self, request):
        """Create a new transition."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Delegate to service
        service = TransitionService(user=request.user)
        transition = service.create_transition(
            workflow=serializer.validated_data['workflow'],
            data=serializer.validated_data
        )

        return Response(
            {
                'status': 'success',
                'data': self.get_serializer(transition).data,
                'message': 'Transition created successfully'
            },
            status=status.HTTP_201_CREATED
        )

    def update(self, request, pk=None):
        """Update transition details."""
        transition = self.get_object()
        serializer = self.get_serializer(transition, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Delegate to service
        service = TransitionService(user=request.user)
        updated_transition = service.update_transition(
            transition=transition,
            data=serializer.validated_data
        )

        return Response(
            {
                'status': 'success',
                'data': self.get_serializer(updated_transition).data,
                'message': 'Transition updated successfully'
            }
        )

    def destroy(self, request, pk=None):
        """Delete transition."""
        transition = self.get_object()

        # Delegate to service
        service = TransitionService(user=request.user)
        service.delete_transition(transition)

        return Response(
            {
                'status': 'success',
                'message': 'Transition deleted successfully'
            },
            status=status.HTTP_204_NO_CONTENT
        )

    @action(detail=True, methods=['post'])
    def add_condition(self, request, pk=None):
        """Add a condition to transition."""
        transition = self.get_object()

        condition_type = request.data.get('condition_type')
        condition_value = request.data.get('condition_value')

        if not condition_type:
            return Response(
                {
                    'status': 'error',
                    'error': {
                        'code': 'MISSING_FIELD',
                        'message': 'condition_type is required'
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Delegate to service
        service = TransitionService(user=request.user)
        service.add_condition(transition, condition_type, condition_value)

        return Response(
            {
                'status': 'success',
                'data': self.get_serializer(transition).data,
                'message': 'Condition added successfully'
            }
        )

    @action(detail=True, methods=['post'])
    def add_validator(self, request, pk=None):
        """Add a validator to transition."""
        transition = self.get_object()

        validator_type = request.data.get('validator_type')
        validator_value = request.data.get('validator_value')

        if not validator_type:
            return Response(
                {
                    'status': 'error',
                    'error': {
                        'code': 'MISSING_FIELD',
                        'message': 'validator_type is required'
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Delegate to service
        service = TransitionService(user=request.user)
        service.add_validator(transition, validator_type, validator_value)

        return Response(
            {
                'status': 'success',
                'data': self.get_serializer(transition).data,
                'message': 'Validator added successfully'
            }
        )

    @action(detail=True, methods=['post'])
    def add_post_function(self, request, pk=None):
        """Add a post-function to transition."""
        transition = self.get_object()

        function_type = request.data.get('function_type')
        function_value = request.data.get('function_value')

        if not function_type:
            return Response(
                {
                    'status': 'error',
                    'error': {
                        'code': 'MISSING_FIELD',
                        'message': 'function_type is required'
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Delegate to service
        service = TransitionService(user=request.user)
        service.add_post_function(transition, function_type, function_value)

        return Response(
            {
                'status': 'success',
                'data': self.get_serializer(transition).data,
                'message': 'Post-function added successfully'
            }
        )


class WorkflowSchemeViewSet(viewsets.ModelViewSet):
    """
    Workflow scheme management endpoints.

    Provides CRUD operations for workflow schemes (project-workflow mappings).
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return WorkflowSchemeCreateSerializer
        return WorkflowSchemeSerializer

    def get_queryset(self):
        """Get schemes for user's projects."""
        # Get projects user has access to
        from apps.projects.models import ProjectMember

        project_ids = ProjectMember.objects.filter(
            user=self.request.user,
            is_active=True
        ).values_list('project_id', flat=True)

        return WorkflowScheme.objects.filter(
            project_id__in=project_ids
        ).select_related('project', 'default_workflow').order_by('project__name')

    def create(self, request):
        """Create a new workflow scheme."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create scheme
        scheme = WorkflowScheme.objects.create(
            created_by=request.user,
            **serializer.validated_data
        )

        return Response(
            {
                'status': 'success',
                'data': WorkflowSchemeSerializer(scheme).data,
                'message': 'Workflow scheme created successfully'
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def set_mapping(self, request, pk=None):
        """Set workflow for an issue type."""
        scheme = self.get_object()

        issue_type_id = request.data.get('issue_type_id')
        workflow_id = request.data.get('workflow_id')

        if not issue_type_id or not workflow_id:
            return Response(
                {
                    'status': 'error',
                    'error': {
                        'code': 'MISSING_FIELDS',
                        'message': 'issue_type_id and workflow_id are required'
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Set mapping
        scheme.set_workflow_for_issue_type(issue_type_id, workflow_id)

        return Response(
            {
                'status': 'success',
                'data': self.get_serializer(scheme).data,
                'message': 'Workflow mapping set successfully'
            }
        )

    @action(detail=True, methods=['delete'], url_path='mappings/(?P<issue_type_id>[^/.]+)')
    def remove_mapping(self, request, pk=None, issue_type_id=None):
        """Remove workflow mapping for an issue type."""
        scheme = self.get_object()

        # Remove mapping
        scheme.remove_workflow_for_issue_type(issue_type_id)

        return Response(
            {
                'status': 'success',
                'message': 'Workflow mapping removed successfully'
            }
        )
