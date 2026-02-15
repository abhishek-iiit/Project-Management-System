"""
Automation serializers.

Following CLAUDE.md best practices:
- Comprehensive validation
- Nested relationships
- Read-only computed fields
"""

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from apps.automation.models import AutomationRule, AutomationExecution, TriggerType, ExecutionStatus


class AutomationRuleSerializer(serializers.ModelSerializer):
    """Serializer for automation rules."""

    # Read-only fields
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    project_key = serializers.CharField(
        source='project.key',
        read_only=True,
        allow_null=True
    )
    trigger_type_display = serializers.CharField(
        source='get_trigger_type_display',
        read_only=True
    )

    # Computed fields
    last_execution = serializers.SerializerMethodField()

    class Meta:
        model = AutomationRule
        fields = [
            'id',
            'organization',
            'organization_name',
            'project',
            'project_key',
            'name',
            'description',
            'trigger_type',
            'trigger_type_display',
            'trigger_config',
            'conditions',
            'actions',
            'is_active',
            'execution_count',
            'last_executed_at',
            'last_execution',
            'created_by',
            'updated_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'organization_name',
            'project_key',
            'trigger_type_display',
            'execution_count',
            'last_executed_at',
            'last_execution',
            'created_by',
            'updated_by',
            'created_at',
            'updated_at',
        ]

    def get_last_execution(self, obj):
        """Get last execution info."""
        execution = obj.executions.first()
        if not execution:
            return None

        return {
            'id': str(execution.id),
            'status': execution.status,
            'created_at': execution.created_at,
            'execution_time_ms': execution.execution_time_ms
        }

    def validate_trigger_config(self, value):
        """Validate trigger configuration."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Trigger config must be a dictionary")
        return value

    def validate_conditions(self, value):
        """Validate conditions."""
        if not isinstance(value, list):
            raise serializers.ValidationError("Conditions must be a list")

        for idx, condition in enumerate(value):
            if not isinstance(condition, dict):
                raise serializers.ValidationError(f"Condition {idx} must be a dictionary")
            if 'type' not in condition:
                raise serializers.ValidationError(f"Condition {idx} must have a 'type'")
            if 'config' not in condition:
                raise serializers.ValidationError(f"Condition {idx} must have a 'config'")

        return value

    def validate_actions(self, value):
        """Validate actions."""
        if not isinstance(value, list):
            raise serializers.ValidationError("Actions must be a list")

        if not value:
            raise serializers.ValidationError("At least one action is required")

        for idx, action in enumerate(value):
            if not isinstance(action, dict):
                raise serializers.ValidationError(f"Action {idx} must be a dictionary")
            if 'type' not in action:
                raise serializers.ValidationError(f"Action {idx} must have a 'type'")
            if 'config' not in action:
                raise serializers.ValidationError(f"Action {idx} must have a 'config'")

        return value


class AutomationRuleCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating automation rules."""

    class Meta:
        model = AutomationRule
        fields = [
            'organization',
            'project',
            'name',
            'description',
            'trigger_type',
            'trigger_config',
            'conditions',
            'actions',
            'is_active',
        ]

    def validate(self, attrs):
        """Cross-field validation."""
        # Validate project belongs to organization
        project = attrs.get('project')
        organization = attrs.get('organization')

        if project and project.organization_id != organization.id:
            raise serializers.ValidationError({
                'project': 'Project must belong to the same organization'
            })

        return attrs


class AutomationExecutionSerializer(serializers.ModelSerializer):
    """Serializer for automation executions."""

    # Read-only fields
    rule_name = serializers.CharField(source='rule.name', read_only=True)
    issue_key = serializers.CharField(
        source='issue.key',
        read_only=True,
        allow_null=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )

    class Meta:
        model = AutomationExecution
        fields = [
            'id',
            'rule',
            'rule_name',
            'issue',
            'issue_key',
            'trigger_event',
            'status',
            'status_display',
            'conditions_passed',
            'conditions_result',
            'actions_executed',
            'actions_result',
            'error_message',
            'error_details',
            'execution_time_ms',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'rule_name',
            'issue_key',
            'status_display',
            'created_at',
            'updated_at',
        ]


class TriggerTypeSerializer(serializers.Serializer):
    """Serializer for trigger type choices."""

    value = serializers.CharField()
    label = serializers.CharField()


class ConditionTypeSerializer(serializers.Serializer):
    """Serializer for available condition types."""

    type = serializers.CharField()
    description = serializers.CharField()
    config_schema = serializers.DictField()


class ActionTypeSerializer(serializers.Serializer):
    """Serializer for available action types."""

    type = serializers.CharField()
    description = serializers.CharField()
    config_schema = serializers.DictField()


class TestRuleSerializer(serializers.Serializer):
    """Serializer for testing automation rules."""

    issue_id = serializers.UUIDField()
    event_type = serializers.CharField()


class RuleStatisticsSerializer(serializers.Serializer):
    """Serializer for rule statistics."""

    total_executions = serializers.IntegerField()
    successful_executions = serializers.IntegerField()
    failed_executions = serializers.IntegerField()
    partial_executions = serializers.IntegerField()
    average_execution_time_ms = serializers.FloatField()
    last_executed_at = serializers.DateTimeField(allow_null=True)
