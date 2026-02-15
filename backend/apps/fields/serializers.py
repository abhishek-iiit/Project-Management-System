"""
Field serializers.

Following CLAUDE.md best practices:
- Comprehensive validation
- Nested relationships
- Read-only computed fields
"""

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from apps.fields.models import (
    FieldDefinition, FieldContext, FieldScheme,
    FieldType
)


class FieldTypeSerializer(serializers.Serializer):
    """Serializer for field type choices."""

    value = serializers.CharField()
    label = serializers.CharField()


class FieldDefinitionSerializer(serializers.ModelSerializer):
    """Serializer for field definitions."""

    # Read-only fields
    organization_id = serializers.UUIDField(source='organization.id', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    created_by_name = serializers.CharField(
        source='created_by.get_full_name',
        read_only=True,
        allow_null=True
    )
    updated_by_name = serializers.CharField(
        source='updated_by.get_full_name',
        read_only=True,
        allow_null=True
    )

    # Display field
    field_type_display = serializers.CharField(
        source='get_field_type_display',
        read_only=True
    )

    class Meta:
        model = FieldDefinition
        fields = [
            'id',
            'organization_id',
            'organization_name',
            'name',
            'description',
            'field_type',
            'field_type_display',
            'config',
            'default_value',
            'is_required',
            'placeholder',
            'help_text',
            'is_active',
            'position',
            'created_by',
            'created_by_name',
            'updated_by',
            'updated_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'organization_id',
            'organization_name',
            'created_by',
            'created_by_name',
            'updated_by',
            'updated_by_name',
            'created_at',
            'updated_at',
        ]

    def validate_field_type(self, value):
        """Validate field type is valid."""
        valid_types = [choice[0] for choice in FieldType.choices]
        if value not in valid_types:
            raise serializers.ValidationError(
                f"Invalid field type. Must be one of: {', '.join(valid_types)}"
            )
        return value

    def validate_config(self, value):
        """Validate field configuration."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Config must be a dictionary")

        # Validate select/multiselect options
        field_type = self.initial_data.get('field_type')
        if field_type in [FieldType.SELECT, FieldType.MULTISELECT]:
            if 'options' not in value or not value['options']:
                raise serializers.ValidationError(
                    "Select fields must have options defined in config"
                )

            # Validate options structure
            options = value['options']
            if not isinstance(options, list):
                raise serializers.ValidationError("Options must be a list")

            for idx, option in enumerate(options):
                if not isinstance(option, dict):
                    raise serializers.ValidationError(
                        f"Option {idx} must be a dictionary"
                    )
                if 'value' not in option or 'label' not in option:
                    raise serializers.ValidationError(
                        f"Option {idx} must have 'value' and 'label' keys"
                    )

        return value

    def validate_default_value(self, value):
        """Validate default value type matches field type."""
        if value is None:
            return value

        field_type = self.initial_data.get('field_type')

        # Type validation based on field type
        if field_type == FieldType.TEXT or field_type == FieldType.TEXTAREA:
            if not isinstance(value, str):
                raise serializers.ValidationError("Default value must be a string")

        elif field_type == FieldType.NUMBER or field_type == FieldType.DECIMAL:
            if not isinstance(value, (int, float)):
                raise serializers.ValidationError("Default value must be a number")

        elif field_type == FieldType.CHECKBOX:
            if not isinstance(value, bool):
                raise serializers.ValidationError("Default value must be a boolean")

        elif field_type == FieldType.MULTISELECT or field_type == FieldType.LABELS:
            if not isinstance(value, list):
                raise serializers.ValidationError("Default value must be a list")

        return value


class FieldDefinitionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating field definitions."""

    class Meta:
        model = FieldDefinition
        fields = [
            'name',
            'description',
            'field_type',
            'config',
            'default_value',
            'is_required',
            'placeholder',
            'help_text',
            'is_active',
            'position',
        ]

    def validate(self, attrs):
        """Cross-field validation."""
        # Validate config matches field type
        field_type = attrs.get('field_type')
        config = attrs.get('config', {})

        if field_type in [FieldType.SELECT, FieldType.MULTISELECT]:
            if 'options' not in config or not config['options']:
                raise serializers.ValidationError({
                    'config': "Select fields must have options defined"
                })

        # Validate default value if provided
        default_value = attrs.get('default_value')
        if default_value is not None:
            # Create temporary field definition to validate
            temp_field = FieldDefinition(
                field_type=field_type,
                config=config
            )
            try:
                temp_field.validate_value(default_value)
            except Exception as e:
                raise serializers.ValidationError({
                    'default_value': f"Invalid default value: {str(e)}"
                })

        return attrs


class FieldDefinitionUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating field definitions."""

    class Meta:
        model = FieldDefinition
        fields = [
            'name',
            'description',
            'config',
            'default_value',
            'is_required',
            'placeholder',
            'help_text',
            'is_active',
            'position',
        ]

    def validate(self, attrs):
        """Cross-field validation."""
        # Get existing field type
        field_type = self.instance.field_type

        # Validate config if provided
        config = attrs.get('config', self.instance.config)

        if field_type in [FieldType.SELECT, FieldType.MULTISELECT]:
            if 'options' not in config or not config['options']:
                raise serializers.ValidationError({
                    'config': "Select fields must have options defined"
                })

        # Validate default value if provided
        default_value = attrs.get('default_value')
        if default_value is not None:
            temp_field = FieldDefinition(
                field_type=field_type,
                config=config
            )
            try:
                temp_field.validate_value(default_value)
            except Exception as e:
                raise serializers.ValidationError({
                    'default_value': f"Invalid default value: {str(e)}"
                })

        return attrs


class FieldContextSerializer(serializers.ModelSerializer):
    """Serializer for field contexts."""

    # Read-only fields
    field_name = serializers.CharField(source='field.name', read_only=True)
    field_type = serializers.CharField(source='field.field_type', read_only=True)
    project_key = serializers.CharField(
        source='project.key',
        read_only=True,
        allow_null=True
    )
    issue_type_name = serializers.CharField(
        source='issue_type.name',
        read_only=True,
        allow_null=True
    )

    # Effective required (context override or field default)
    effective_required = serializers.SerializerMethodField()

    class Meta:
        model = FieldContext
        fields = [
            'id',
            'field',
            'field_name',
            'field_type',
            'project',
            'project_key',
            'issue_type',
            'issue_type_name',
            'is_required',
            'effective_required',
            'is_visible',
            'position',
            'created_by',
            'updated_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'field_name',
            'field_type',
            'project_key',
            'issue_type_name',
            'effective_required',
            'created_by',
            'updated_by',
            'created_at',
            'updated_at',
        ]

    def get_effective_required(self, obj):
        """Get effective required setting."""
        return obj.get_effective_required()

    def validate(self, attrs):
        """Validate field context."""
        # Ensure field belongs to same organization as project (if project specified)
        field = attrs.get('field')
        project = attrs.get('project')

        if project and field:
            if field.organization_id != project.organization_id:
                raise serializers.ValidationError({
                    'field': "Field must belong to same organization as project"
                })

        return attrs


class FieldContextCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating field contexts."""

    class Meta:
        model = FieldContext
        fields = [
            'field',
            'project',
            'issue_type',
            'is_required',
            'is_visible',
            'position',
        ]

    def validate(self, attrs):
        """Validate field context creation."""
        field = attrs.get('field')
        project = attrs.get('project')
        issue_type = attrs.get('issue_type')

        # Check for duplicate context
        existing = FieldContext.objects.filter(
            field=field,
            project=project,
            issue_type=issue_type
        ).exists()

        if existing:
            raise serializers.ValidationError(
                "Field context already exists for this combination"
            )

        # Validate organization consistency
        if project and field:
            if field.organization_id != project.organization_id:
                raise serializers.ValidationError({
                    'field': "Field must belong to same organization as project"
                })

        return attrs


class FieldSchemeSerializer(serializers.ModelSerializer):
    """Serializer for field schemes."""

    # Read-only fields
    project_key = serializers.CharField(source='project.key', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)

    class Meta:
        model = FieldScheme
        fields = [
            'id',
            'project',
            'project_key',
            'project_name',
            'name',
            'description',
            'field_configs',
            'is_active',
            'created_by',
            'updated_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'project_key',
            'project_name',
            'created_by',
            'updated_by',
            'created_at',
            'updated_at',
        ]

    def validate_field_configs(self, value):
        """Validate field configurations."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Field configs must be a dictionary")

        # Validate structure (field_id: config)
        for field_id, config in value.items():
            if not isinstance(config, dict):
                raise serializers.ValidationError(
                    f"Config for field {field_id} must be a dictionary"
                )

        return value


class FieldSchemeCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating field schemes."""

    class Meta:
        model = FieldScheme
        fields = [
            'project',
            'name',
            'description',
            'field_configs',
            'is_active',
        ]

    def validate_project(self, value):
        """Validate project doesn't already have a scheme."""
        # Check for existing scheme
        existing = FieldScheme.objects.filter(project=value).exists()
        if existing:
            raise serializers.ValidationError(
                "Project already has a field scheme"
            )
        return value


class FieldRenderConfigSerializer(serializers.Serializer):
    """Serializer for field rendering configuration (for frontend)."""

    id = serializers.UUIDField()
    name = serializers.CharField()
    field_type = serializers.CharField()
    placeholder = serializers.CharField(allow_blank=True)
    help_text = serializers.CharField(allow_blank=True)
    is_required = serializers.BooleanField()
    default_value = serializers.JSONField(allow_null=True)
    config = serializers.JSONField()


class FieldValidationSerializer(serializers.Serializer):
    """Serializer for validating field values."""

    field_id = serializers.UUIDField()
    value = serializers.JSONField()


class BulkFieldContextCreateSerializer(serializers.Serializer):
    """Serializer for bulk creating field contexts."""

    field_id = serializers.UUIDField()
    contexts = serializers.ListField(
        child=serializers.DictField(),
        min_length=1
    )


class FieldReorderSerializer(serializers.Serializer):
    """Serializer for reordering fields."""

    field_order = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1
    )


class FieldConfigUpdateSerializer(serializers.Serializer):
    """Serializer for updating field config in scheme."""

    field_id = serializers.UUIDField()
    config = serializers.JSONField()


class CopyFieldContextsSerializer(serializers.Serializer):
    """Serializer for copying field contexts between projects."""

    source_project_id = serializers.UUIDField()
    target_project_id = serializers.UUIDField()

    def validate(self, attrs):
        """Validate projects are different."""
        if attrs['source_project_id'] == attrs['target_project_id']:
            raise serializers.ValidationError(
                "Source and target projects must be different"
            )
        return attrs
