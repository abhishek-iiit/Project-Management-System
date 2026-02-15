"""
Project serializers for API endpoints.

Following CLAUDE.md best practices:
- Efficient data transformation
- Nested relationships with prefetch optimization
- Validation at serializer level
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.projects.models import Project, ProjectMember, ProjectRole, ProjectTemplate
from apps.organizations.models import Organization

User = get_user_model()


class ProjectRoleSerializer(serializers.ModelSerializer):
    """Serializer for project roles."""

    permissions_count = serializers.SerializerMethodField()

    class Meta:
        model = ProjectRole
        fields = [
            'id', 'name', 'description', 'permissions',
            'is_default', 'organization',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_permissions_count(self, obj):
        """Get count of permissions."""
        if isinstance(obj.permissions, dict):
            return len(obj.permissions)
        return 0

    def validate_permissions(self, value):
        """Validate permissions structure."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Permissions must be a dictionary")
        return value


class ProjectMemberSerializer(serializers.ModelSerializer):
    """Serializer for project members."""

    # Nested user data (uses select_related in queryset)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    # Role details (uses select_related in queryset)
    role_name = serializers.CharField(source='role.name', read_only=True, allow_null=True)

    # Computed permissions
    effective_permissions = serializers.SerializerMethodField()

    class Meta:
        model = ProjectMember
        fields = [
            'id', 'project', 'user', 'user_email', 'user_name',
            'role', 'role_name', 'is_admin', 'custom_permissions',
            'effective_permissions',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_effective_permissions(self, obj):
        """Get all effective permissions for this member."""
        permissions = {}

        # Start with role permissions
        if obj.role and obj.role.permissions:
            permissions.update(obj.role.permissions)

        # Override with custom permissions
        if obj.custom_permissions:
            permissions.update(obj.custom_permissions)

        # Admins get all permissions
        if obj.is_admin:
            permissions.update({
                'manage_project': True,
                'manage_members': True,
                'manage_issues': True,
                'delete_project': True,
            })

        return permissions


class ProjectMinimalSerializer(serializers.ModelSerializer):
    """Minimal project serializer for nested relationships."""

    organization_name = serializers.CharField(source='organization.name', read_only=True)
    lead_name = serializers.CharField(source='lead.full_name', read_only=True, allow_null=True)

    # Annotated fields (from queryset)
    members_count = serializers.IntegerField(read_only=True)
    issues_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Project
        fields = [
            'id', 'name', 'key', 'description',
            'organization', 'organization_name',
            'lead', 'lead_name',
            'project_type', 'template',
            'is_active', 'is_private',
            'members_count', 'issues_count',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ProjectSerializer(serializers.ModelSerializer):
    """Full project serializer with all details."""

    # Organization details (uses select_related)
    organization_name = serializers.CharField(source='organization.name', read_only=True)

    # Lead details (uses select_related)
    lead_email = serializers.EmailField(source='lead.email', read_only=True, allow_null=True)
    lead_name = serializers.CharField(source='lead.full_name', read_only=True, allow_null=True)

    # Creator details (uses select_related via AuditMixin)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    # Annotated fields (from queryset)
    members_count = serializers.IntegerField(read_only=True)
    issues_count = serializers.IntegerField(read_only=True)

    # Nested relationships (uses prefetch_related)
    members = ProjectMemberSerializer(source='project_members', many=True, read_only=True)

    # Settings
    settings_summary = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id', 'name', 'key', 'description', 'avatar',
            'organization', 'organization_name',
            'lead', 'lead_email', 'lead_name',
            'project_type', 'template',
            'settings', 'settings_summary',
            'is_active', 'is_private',
            'members_count', 'issues_count',
            'members',
            'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_by', 'created_at', 'updated_at',
            'members_count', 'issues_count'
        ]

    def get_settings_summary(self, obj):
        """Get summary of project settings."""
        if not obj.settings:
            return {}

        return {
            'workflow_enabled': obj.settings.get('workflow_enabled', True),
            'allow_subtasks': obj.settings.get('allow_subtasks', True),
            'default_issue_type': obj.settings.get('default_issue_type'),
            'time_tracking_enabled': obj.settings.get('time_tracking_enabled', False),
        }


class ProjectCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating projects."""

    # Organization is required but not editable after creation
    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(),
        required=True
    )

    # Lead defaults to current user if not specified
    lead = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Project
        fields = [
            'name', 'key', 'description', 'avatar',
            'organization', 'lead',
            'project_type', 'template',
            'settings', 'is_private'
        ]

    def validate_key(self, value):
        """Validate project key format and uniqueness."""
        # Key should be uppercase alphanumeric
        if not value.isupper():
            raise serializers.ValidationError("Project key must be uppercase")

        if not value.isalnum():
            raise serializers.ValidationError("Project key must be alphanumeric")

        if len(value) < 2 or len(value) > 10:
            raise serializers.ValidationError("Project key must be 2-10 characters")

        return value

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
        # Validate key uniqueness within organization
        organization = data.get('organization')
        key = data.get('key')

        if organization and key:
            if Project.objects.filter(
                organization=organization,
                key=key
            ).exists():
                raise serializers.ValidationError({
                    'key': 'Project with this key already exists in the organization'
                })

        return data


class AddMemberSerializer(serializers.Serializer):
    """Serializer for adding members to project."""

    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=True
    )

    role = serializers.PrimaryKeyRelatedField(
        queryset=ProjectRole.objects.all(),
        required=False,
        allow_null=True
    )

    is_admin = serializers.BooleanField(default=False)

    def validate_user(self, value):
        """Validate user exists and has access."""
        project = self.context.get('project')

        if not project:
            return value

        # Check if user is member of project's organization
        if not project.organization.organization_members.filter(
            user=value,
            is_active=True
        ).exists():
            raise serializers.ValidationError(
                "User is not a member of the project's organization"
            )

        # Check if already project member
        if ProjectMember.objects.filter(
            project=project,
            user=value,
            is_active=True
        ).exists():
            raise serializers.ValidationError(
                "User is already a project member"
            )

        return value

    def validate_role(self, value):
        """Validate role belongs to project's organization."""
        project = self.context.get('project')

        if value and project:
            if value.organization != project.organization:
                raise serializers.ValidationError(
                    "Role does not belong to the project's organization"
                )

        return value


class UpdateMemberRoleSerializer(serializers.Serializer):
    """Serializer for updating member role/admin status."""

    role = serializers.PrimaryKeyRelatedField(
        queryset=ProjectRole.objects.all(),
        required=False,
        allow_null=True
    )

    is_admin = serializers.BooleanField(required=False)

    custom_permissions = serializers.JSONField(required=False, allow_null=True)

    def validate_role(self, value):
        """Validate role belongs to project's organization."""
        project = self.context.get('project')

        if value and project:
            if value.organization != project.organization:
                raise serializers.ValidationError(
                    "Role does not belong to the project's organization"
                )

        return value

    def validate_custom_permissions(self, value):
        """Validate custom permissions structure."""
        if value is not None and not isinstance(value, dict):
            raise serializers.ValidationError(
                "Custom permissions must be a dictionary"
            )
        return value

    def validate(self, data):
        """Ensure at least one field is being updated."""
        if not any(field in data for field in ['role', 'is_admin', 'custom_permissions']):
            raise serializers.ValidationError(
                "At least one field must be provided for update"
            )
        return data


class ProjectTemplateSerializer(serializers.ModelSerializer):
    """Serializer for project templates."""

    organization_name = serializers.CharField(source='organization.name', read_only=True)
    config_summary = serializers.SerializerMethodField()

    class Meta:
        model = ProjectTemplate
        fields = [
            'id', 'name', 'description',
            'organization', 'organization_name',
            'template_type', 'config', 'config_summary',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_config_summary(self, obj):
        """Get summary of template configuration."""
        if not obj.config:
            return {}

        return {
            'has_workflow': 'workflow' in obj.config,
            'has_roles': 'roles' in obj.config,
            'has_issue_types': 'issue_types' in obj.config,
            'settings_count': len(obj.config.get('settings', {})),
        }

    def validate_config(self, value):
        """Validate template configuration structure."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Config must be a dictionary")
        return value
