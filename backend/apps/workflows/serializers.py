"""
Workflow serializers for API endpoints.

Following CLAUDE.md best practices:
- Efficient data transformation
- Nested relationships with prefetch optimization
- Validation at serializer level
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.workflows.models import Workflow, Status, Transition, WorkflowScheme, StatusCategory
from apps.organizations.models import Organization
from apps.projects.models import Project

User = get_user_model()


class StatusSerializer(serializers.ModelSerializer):
    """Serializer for status model."""

    category_display = serializers.CharField(source='get_category_display', read_only=True)
    outgoing_transitions_count = serializers.SerializerMethodField()
    incoming_transitions_count = serializers.SerializerMethodField()

    class Meta:
        model = Status
        fields = [
            'id', 'workflow', 'name', 'description',
            'category', 'category_display',
            'is_initial', 'is_active', 'position',
            'outgoing_transitions_count', 'incoming_transitions_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_outgoing_transitions_count(self, obj):
        """Get count of outgoing transitions."""
        return obj.outgoing_transitions.filter(is_active=True).count()

    def get_incoming_transitions_count(self, obj):
        """Get count of incoming transitions."""
        return obj.incoming_transitions.filter(is_active=True).count()

    def validate(self, data):
        """Cross-field validation."""
        # Ensure only one initial status per workflow
        if data.get('is_initial'):
            workflow = data.get('workflow') or (self.instance.workflow if self.instance else None)
            if workflow:
                existing = Status.objects.filter(
                    workflow=workflow,
                    is_initial=True
                ).exclude(id=self.instance.id if self.instance else None)

                if existing.exists():
                    raise serializers.ValidationError({
                        'is_initial': 'Only one initial status allowed per workflow'
                    })

        return data


class StatusMinimalSerializer(serializers.ModelSerializer):
    """Minimal status serializer for nested relationships."""

    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = Status
        fields = ['id', 'name', 'category', 'category_display', 'is_initial']
        read_only_fields = ['id']


class TransitionSerializer(serializers.ModelSerializer):
    """Serializer for transition model."""

    # Nested status data (uses select_related)
    from_status_name = serializers.CharField(source='from_status.name', read_only=True, allow_null=True)
    to_status_name = serializers.CharField(source='to_status.name', read_only=True)

    # Configuration summaries
    conditions_count = serializers.SerializerMethodField()
    validators_count = serializers.SerializerMethodField()
    post_functions_count = serializers.SerializerMethodField()

    class Meta:
        model = Transition
        fields = [
            'id', 'workflow', 'name', 'description',
            'from_status', 'from_status_name',
            'to_status', 'to_status_name',
            'conditions', 'conditions_count',
            'validators', 'validators_count',
            'post_functions', 'post_functions_count',
            'is_active', 'position',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_conditions_count(self, obj):
        """Get count of conditions."""
        return len(obj.conditions) if obj.conditions else 0

    def get_validators_count(self, obj):
        """Get count of validators."""
        return len(obj.validators) if obj.validators else 0

    def get_post_functions_count(self, obj):
        """Get count of post-functions."""
        return len(obj.post_functions) if obj.post_functions else 0

    def validate(self, data):
        """Cross-field validation."""
        from_status = data.get('from_status')
        to_status = data.get('to_status')
        workflow = data.get('workflow') or (self.instance.workflow if self.instance else None)

        # Validate statuses belong to workflow
        if from_status and from_status.workflow != workflow:
            raise serializers.ValidationError({
                'from_status': 'From status must belong to the same workflow'
            })

        if to_status and to_status.workflow != workflow:
            raise serializers.ValidationError({
                'to_status': 'To status must belong to the same workflow'
            })

        # Validate JSONB fields
        if 'conditions' in data and data['conditions'] and not isinstance(data['conditions'], dict):
            raise serializers.ValidationError({
                'conditions': 'Conditions must be a dictionary'
            })

        if 'validators' in data and data['validators'] and not isinstance(data['validators'], dict):
            raise serializers.ValidationError({
                'validators': 'Validators must be a dictionary'
            })

        if 'post_functions' in data and data['post_functions'] and not isinstance(data['post_functions'], dict):
            raise serializers.ValidationError({
                'post_functions': 'Post-functions must be a dictionary'
            })

        return data


class TransitionMinimalSerializer(serializers.ModelSerializer):
    """Minimal transition serializer for nested relationships."""

    from_status_name = serializers.CharField(source='from_status.name', read_only=True, allow_null=True)
    to_status_name = serializers.CharField(source='to_status.name', read_only=True)

    class Meta:
        model = Transition
        fields = [
            'id', 'name',
            'from_status', 'from_status_name',
            'to_status', 'to_status_name'
        ]
        read_only_fields = ['id']


class WorkflowSerializer(serializers.ModelSerializer):
    """Full workflow serializer with all details."""

    # Organization details
    organization_name = serializers.CharField(source='organization.name', read_only=True)

    # Creator details
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    # Nested relationships (uses prefetch_related)
    statuses = StatusSerializer(many=True, read_only=True)
    transitions = TransitionSerializer(many=True, read_only=True)

    # Counts
    statuses_count = serializers.SerializerMethodField()
    transitions_count = serializers.SerializerMethodField()

    # Initial status
    initial_status = serializers.SerializerMethodField()

    class Meta:
        model = Workflow
        fields = [
            'id', 'name', 'description',
            'organization', 'organization_name',
            'is_active', 'is_default',
            'statuses', 'statuses_count',
            'transitions', 'transitions_count',
            'initial_status',
            'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_by', 'created_at', 'updated_at',
            'statuses_count', 'transitions_count'
        ]

    def get_statuses_count(self, obj):
        """Get count of active statuses."""
        return obj.statuses.filter(is_active=True).count()

    def get_transitions_count(self, obj):
        """Get count of active transitions."""
        return obj.transitions.filter(is_active=True).count()

    def get_initial_status(self, obj):
        """Get initial status."""
        initial = obj.get_initial_status()
        if initial:
            return StatusMinimalSerializer(initial).data
        return None


class WorkflowMinimalSerializer(serializers.ModelSerializer):
    """Minimal workflow serializer for nested relationships."""

    organization_name = serializers.CharField(source='organization.name', read_only=True)
    statuses_count = serializers.SerializerMethodField()

    class Meta:
        model = Workflow
        fields = [
            'id', 'name', 'description',
            'organization', 'organization_name',
            'is_active', 'is_default',
            'statuses_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_statuses_count(self, obj):
        """Get count of active statuses."""
        return obj.statuses.filter(is_active=True).count()


class WorkflowCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating workflows."""

    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(),
        required=True
    )

    class Meta:
        model = Workflow
        fields = [
            'name', 'description',
            'organization',
            'is_active', 'is_default'
        ]

    def validate_organization(self, value):
        """Validate user has access to organization."""
        user = self.context['request'].user

        # Check if user is member of organization
        if not value.organization_members.filter(
            user=user,
            is_active=True
        ).exists():
            raise serializers.ValidationError(
                "You are not a member of this organization"
            )

        return value

    def validate(self, data):
        """Cross-field validation."""
        # Validate name uniqueness within organization
        organization = data.get('organization')
        name = data.get('name')

        if organization and name:
            if Workflow.objects.filter(
                organization=organization,
                name=name
            ).exists():
                raise serializers.ValidationError({
                    'name': 'Workflow with this name already exists in the organization'
                })

        return data


class WorkflowSchemeSerializer(serializers.ModelSerializer):
    """Serializer for workflow scheme model."""

    # Project details
    project_key = serializers.CharField(source='project.key', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)

    # Default workflow details
    default_workflow_name = serializers.CharField(source='default_workflow.name', read_only=True)

    # Mappings summary
    mappings_count = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowScheme
        fields = [
            'id', 'project', 'project_key', 'project_name',
            'name', 'description',
            'default_workflow', 'default_workflow_name',
            'mappings', 'mappings_count',
            'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_mappings_count(self, obj):
        """Get count of issue type mappings."""
        return len(obj.mappings) if obj.mappings else 0

    def validate_mappings(self, value):
        """Validate mappings structure."""
        if value and not isinstance(value, dict):
            raise serializers.ValidationError("Mappings must be a dictionary")
        return value


class WorkflowSchemeCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating workflow schemes."""

    project = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(),
        required=True
    )

    default_workflow = serializers.PrimaryKeyRelatedField(
        queryset=Workflow.objects.all(),
        required=True
    )

    class Meta:
        model = WorkflowScheme
        fields = [
            'project', 'name', 'description',
            'default_workflow', 'mappings'
        ]

    def validate_project(self, value):
        """Validate user has access to project."""
        user = self.context['request'].user

        # Check if user is project member
        if not value.has_member(user):
            raise serializers.ValidationError(
                "You are not a member of this project"
            )

        # Check if project already has a scheme
        if WorkflowScheme.objects.filter(project=value).exists():
            raise serializers.ValidationError(
                "Project already has a workflow scheme"
            )

        return value

    def validate_default_workflow(self, value):
        """Validate workflow belongs to project's organization."""
        project = self.initial_data.get('project')
        if project:
            try:
                project_obj = Project.objects.get(id=project)
                if value.organization != project_obj.organization:
                    raise serializers.ValidationError(
                        "Workflow must belong to the project's organization"
                    )
            except Project.DoesNotExist:
                pass

        return value


class CloneWorkflowSerializer(serializers.Serializer):
    """Serializer for cloning workflows."""

    new_name = serializers.CharField(max_length=100, required=True)
    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(),
        required=False
    )

    def validate_new_name(self, value):
        """Validate new name doesn't exist."""
        workflow = self.context.get('workflow')
        organization = self.initial_data.get('organization')

        # Use original organization if not specified
        org = organization if organization else (workflow.organization if workflow else None)

        if org and Workflow.objects.filter(organization=org, name=value).exists():
            raise serializers.ValidationError(
                "Workflow with this name already exists in the organization"
            )

        return value
