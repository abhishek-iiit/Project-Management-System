"""
Automation views.

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
from django.db.models import Count, Avg, Q

from apps.automation.models import AutomationRule, AutomationExecution, TriggerType, ExecutionStatus
from apps.automation.serializers import (
    AutomationRuleSerializer,
    AutomationRuleCreateSerializer,
    AutomationExecutionSerializer,
    TriggerTypeSerializer,
    ConditionTypeSerializer,
    ActionTypeSerializer,
    TestRuleSerializer,
    RuleStatisticsSerializer,
)
from apps.automation.services.automation_engine import automation_engine
from apps.automation.triggers.issue_triggers import TRIGGER_REGISTRY
from apps.automation.conditions.field_conditions import CONDITION_REGISTRY
from apps.automation.actions.issue_actions import ACTION_REGISTRY
from apps.common.permissions import IsOrganizationMember


class AutomationRuleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for automation rules.

    Endpoints:
    - GET /automation-rules/ - List all automation rules
    - POST /automation-rules/ - Create automation rule
    - GET /automation-rules/{id}/ - Get automation rule
    - PUT /automation-rules/{id}/ - Update automation rule
    - PATCH /automation-rules/{id}/ - Partial update automation rule
    - DELETE /automation-rules/{id}/ - Delete automation rule
    - POST /automation-rules/{id}/test/ - Test automation rule
    - GET /automation-rules/{id}/statistics/ - Get rule statistics
    - GET /automation-rules/trigger-types/ - Get available trigger types
    - GET /automation-rules/condition-types/ - Get available condition types
    - GET /automation-rules/action-types/ - Get available action types
    """

    permission_classes = [IsAuthenticated, IsOrganizationMember]
    serializer_class = AutomationRuleSerializer
    lookup_field = 'id'

    def get_queryset(self):
        """Get automation rules for current organization."""
        if not hasattr(self.request.user, 'current_organization'):
            return AutomationRule.objects.none()

        return AutomationRule.objects.filter(
            organization=self.request.user.current_organization
        ).with_full_details().prefetch_related('executions')

    def get_serializer_class(self):
        """Get appropriate serializer class."""
        if self.action == 'create':
            return AutomationRuleCreateSerializer
        return AutomationRuleSerializer

    @extend_schema(
        summary="List automation rules",
        parameters=[
            OpenApiParameter('project_id', str, description='Filter by project'),
            OpenApiParameter('trigger_type', str, description='Filter by trigger type'),
            OpenApiParameter('is_active', bool, description='Filter by active status'),
        ]
    )
    def list(self, request):
        """List automation rules with optional filters."""
        queryset = self.get_queryset()

        # Filter by project
        project_id = request.query_params.get('project_id')
        if project_id:
            queryset = queryset.filter(
                Q(project_id=project_id) | Q(project__isnull=True)
            )

        # Filter by trigger type
        trigger_type = request.query_params.get('trigger_type')
        if trigger_type:
            queryset = queryset.filter(trigger_type=trigger_type)

        # Filter by active status
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            is_active = is_active.lower() == 'true'
            queryset = queryset.filter(is_active=is_active)

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'status': 'success',
            'data': serializer.data
        })

    @extend_schema(summary="Create automation rule")
    def create(self, request):
        """Create a new automation rule."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Set audit fields
        rule = serializer.save(
            created_by=request.user,
            updated_by=request.user
        )

        return Response({
            'status': 'success',
            'data': AutomationRuleSerializer(rule).data,
            'message': 'Automation rule created successfully'
        }, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Get automation rule")
    def retrieve(self, request, id=None):
        """Get a specific automation rule."""
        rule = self.get_object()
        serializer = self.get_serializer(rule)

        return Response({
            'status': 'success',
            'data': serializer.data
        })

    @extend_schema(summary="Update automation rule")
    def update(self, request, id=None):
        """Update an automation rule."""
        rule = self.get_object()
        serializer = self.get_serializer(rule, data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_rule = serializer.save(updated_by=request.user)

        return Response({
            'status': 'success',
            'data': AutomationRuleSerializer(updated_rule).data,
            'message': 'Automation rule updated successfully'
        })

    @extend_schema(summary="Partially update automation rule")
    def partial_update(self, request, id=None):
        """Partially update an automation rule."""
        rule = self.get_object()
        serializer = self.get_serializer(rule, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated_rule = serializer.save(updated_by=request.user)

        return Response({
            'status': 'success',
            'data': AutomationRuleSerializer(updated_rule).data,
            'message': 'Automation rule updated successfully'
        })

    @extend_schema(summary="Delete automation rule")
    def destroy(self, request, id=None):
        """Delete an automation rule."""
        rule = self.get_object()
        rule.delete()

        return Response({
            'status': 'success',
            'message': 'Automation rule deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        summary="Test automation rule",
        request=TestRuleSerializer,
        responses={200: OpenApiResponse(description='Test result')}
    )
    @action(detail=True, methods=['post'])
    def test(self, request, id=None):
        """Test an automation rule against a specific issue."""
        rule = self.get_object()
        serializer = TestRuleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from apps.issues.models import Issue

        # Get issue
        issue = Issue.objects.get(id=serializer.validated_data['issue_id'])

        # Build event data
        event_data = {
            'issue': issue,
            'user': request.user,
            'trigger_type': rule.trigger_type,
            'event_type': serializer.validated_data['event_type'],
            'changed_fields': [],
            'changes': {}
        }

        # Execute rule
        execution = automation_engine.execute_rule(rule, event_data)

        return Response({
            'status': 'success',
            'data': AutomationExecutionSerializer(execution).data,
            'message': 'Rule tested successfully'
        })

    @extend_schema(
        summary="Get rule statistics",
        responses={200: RuleStatisticsSerializer}
    )
    @action(detail=True, methods=['get'])
    def statistics(self, request, id=None):
        """Get statistics for an automation rule."""
        rule = self.get_object()

        # Calculate statistics
        executions = rule.executions.all()
        stats = executions.aggregate(
            total=Count('id'),
            successful=Count('id', filter=Q(status=ExecutionStatus.SUCCESS)),
            failed=Count('id', filter=Q(status=ExecutionStatus.FAILED)),
            partial=Count('id', filter=Q(status=ExecutionStatus.PARTIAL)),
            avg_time=Avg('execution_time_ms')
        )

        statistics = {
            'total_executions': stats['total'] or 0,
            'successful_executions': stats['successful'] or 0,
            'failed_executions': stats['failed'] or 0,
            'partial_executions': stats['partial'] or 0,
            'average_execution_time_ms': stats['avg_time'] or 0.0,
            'last_executed_at': rule.last_executed_at
        }

        return Response({
            'status': 'success',
            'data': statistics
        })

    @extend_schema(
        summary="Get available trigger types",
        responses={200: TriggerTypeSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def trigger_types(self, request):
        """Get available trigger types."""
        types_data = [
            {'value': choice[0], 'label': choice[1]}
            for choice in TriggerType.choices
        ]

        serializer = TriggerTypeSerializer(types_data, many=True)
        return Response({
            'status': 'success',
            'data': serializer.data
        })

    @extend_schema(
        summary="Get available condition types",
        responses={200: ConditionTypeSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def condition_types(self, request):
        """Get available condition types."""
        conditions_data = [
            {
                'type': condition_type,
                'description': f'{condition_type} condition',
                'config_schema': {}
            }
            for condition_type in CONDITION_REGISTRY.keys()
        ]

        serializer = ConditionTypeSerializer(conditions_data, many=True)
        return Response({
            'status': 'success',
            'data': serializer.data
        })

    @extend_schema(
        summary="Get available action types",
        responses={200: ActionTypeSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def action_types(self, request):
        """Get available action types."""
        actions_data = [
            {
                'type': action_type,
                'description': f'{action_type} action',
                'config_schema': {}
            }
            for action_type in ACTION_REGISTRY.keys()
        ]

        serializer = ActionTypeSerializer(actions_data, many=True)
        return Response({
            'status': 'success',
            'data': serializer.data
        })


class AutomationExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for automation executions (read-only).

    Endpoints:
    - GET /automation-executions/ - List all automation executions
    - GET /automation-executions/{id}/ - Get automation execution
    """

    permission_classes = [IsAuthenticated, IsOrganizationMember]
    serializer_class = AutomationExecutionSerializer
    lookup_field = 'id'

    def get_queryset(self):
        """Get automation executions for current organization."""
        if not hasattr(self.request.user, 'current_organization'):
            return AutomationExecution.objects.none()

        return AutomationExecution.objects.filter(
            rule__organization=self.request.user.current_organization
        ).with_full_details()

    @extend_schema(
        summary="List automation executions",
        parameters=[
            OpenApiParameter('rule_id', str, description='Filter by rule'),
            OpenApiParameter('issue_id', str, description='Filter by issue'),
            OpenApiParameter('status', str, description='Filter by status'),
        ]
    )
    def list(self, request):
        """List automation executions with optional filters."""
        queryset = self.get_queryset()

        # Filter by rule
        rule_id = request.query_params.get('rule_id')
        if rule_id:
            queryset = queryset.filter(rule_id=rule_id)

        # Filter by issue
        issue_id = request.query_params.get('issue_id')
        if issue_id:
            queryset = queryset.filter(issue_id=issue_id)

        # Filter by status
        exec_status = request.query_params.get('status')
        if exec_status:
            queryset = queryset.filter(status=exec_status)

        # Order by most recent first
        queryset = queryset.order_by('-created_at')

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'status': 'success',
            'data': serializer.data
        })

    @extend_schema(summary="Get automation execution")
    def retrieve(self, request, id=None):
        """Get a specific automation execution."""
        execution = self.get_object()
        serializer = self.get_serializer(execution)

        return Response({
            'status': 'success',
            'data': serializer.data
        })
