"""
Custom field models for dynamic field definitions.

Following CLAUDE.md best practices:
- Fat models with business logic
- JSONB for flexible configurations
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from apps.common.models import BaseModel, AuditMixin
import json


class FieldType(models.TextChoices):
    """Available field types."""
    TEXT = 'text', _('Single-line Text')
    TEXTAREA = 'textarea', _('Multi-line Text')
    NUMBER = 'number', _('Number')
    DECIMAL = 'decimal', _('Decimal')
    DATE = 'date', _('Date')
    DATETIME = 'datetime', _('Date & Time')
    SELECT = 'select', _('Select (Single)')
    MULTISELECT = 'multiselect', _('Multi-select')
    CHECKBOX = 'checkbox', _('Checkbox')
    USER = 'user', _('User Picker')
    URL = 'url', _('URL')
    EMAIL = 'email', _('Email')
    LABELS = 'labels', _('Labels')


class FieldDefinition(BaseModel, AuditMixin):
    """
    Custom field definition/schema.

    Defines the structure and behavior of custom fields that can be
    added to issues dynamically.
    """

    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='field_definitions',
        help_text=_('Organization this field belongs to')
    )

    name = models.CharField(
        _('name'),
        max_length=100,
        help_text=_('Field name (e.g., "Sprint", "Story Points")')
    )

    description = models.TextField(
        _('description'),
        blank=True,
        help_text=_('Field description')
    )

    field_type = models.CharField(
        _('field type'),
        max_length=20,
        choices=FieldType.choices,
        help_text=_('Type of field')
    )

    # Configuration (JSONB)
    config = models.JSONField(
        _('configuration'),
        default=dict,
        blank=True,
        help_text=_('Field configuration (options, validation rules, etc.)')
    )

    # Default value
    default_value = models.JSONField(
        _('default value'),
        null=True,
        blank=True,
        help_text=_('Default value for this field')
    )

    # Validation
    is_required = models.BooleanField(
        _('is required'),
        default=False,
        help_text=_('Whether this field is required')
    )

    # UI
    placeholder = models.CharField(
        _('placeholder'),
        max_length=255,
        blank=True,
        help_text=_('Placeholder text for UI')
    )

    help_text = models.TextField(
        _('help text'),
        blank=True,
        help_text=_('Help text shown to users')
    )

    # Status
    is_active = models.BooleanField(
        _('is active'),
        default=True,
        db_index=True,
        help_text=_('Whether this field is active')
    )

    # Display order
    position = models.PositiveIntegerField(
        _('position'),
        default=0,
        help_text=_('Display order')
    )

    class Meta:
        db_table = 'field_definitions'
        verbose_name = _('field definition')
        verbose_name_plural = _('field definitions')
        ordering = ['organization', 'position', 'name']
        unique_together = [['organization', 'name']]
        indexes = [
            models.Index(fields=['organization', 'name']),
            models.Index(fields=['organization', 'is_active']),
            models.Index(fields=['organization', 'field_type']),
        ]

    def __str__(self):
        """String representation."""
        return f"{self.name} ({self.get_field_type_display()})"

    def __repr__(self):
        """Developer-friendly representation."""
        return f"<FieldDefinition name={self.name} type={self.field_type}>"

    def clean(self):
        """Validate field definition."""
        super().clean()

        # Validate config based on field type
        if self.field_type in [FieldType.SELECT, FieldType.MULTISELECT]:
            if 'options' not in self.config or not self.config['options']:
                raise ValidationError({
                    'config': _('Select fields must have options defined')
                })

        # Validate default value type
        if self.default_value is not None:
            try:
                self.validate_value(self.default_value)
            except ValidationError as e:
                raise ValidationError({
                    'default_value': f'Invalid default value: {e}'
                })

    def validate_value(self, value):
        """
        Validate a value against this field definition.

        Args:
            value: Value to validate

        Raises:
            ValidationError: If value is invalid
        """
        # Required check
        if self.is_required and not value:
            raise ValidationError(f'{self.name} is required')

        if not value:
            return  # Empty optional field is valid

        # Type-specific validation
        if self.field_type == FieldType.TEXT:
            if not isinstance(value, str):
                raise ValidationError(f'{self.name} must be a string')
            max_length = self.config.get('max_length', 255)
            if len(value) > max_length:
                raise ValidationError(
                    f'{self.name} must be at most {max_length} characters'
                )

        elif self.field_type == FieldType.TEXTAREA:
            if not isinstance(value, str):
                raise ValidationError(f'{self.name} must be a string')

        elif self.field_type == FieldType.NUMBER:
            if not isinstance(value, (int, float)):
                raise ValidationError(f'{self.name} must be a number')
            min_value = self.config.get('min_value')
            max_value = self.config.get('max_value')
            if min_value is not None and value < min_value:
                raise ValidationError(f'{self.name} must be at least {min_value}')
            if max_value is not None and value > max_value:
                raise ValidationError(f'{self.name} must be at most {max_value}')

        elif self.field_type == FieldType.DECIMAL:
            if not isinstance(value, (int, float)):
                raise ValidationError(f'{self.name} must be a number')

        elif self.field_type in [FieldType.DATE, FieldType.DATETIME]:
            if not isinstance(value, str):
                raise ValidationError(f'{self.name} must be a date string')

        elif self.field_type == FieldType.SELECT:
            options = self.config.get('options', [])
            valid_values = [opt['value'] for opt in options]
            if value not in valid_values:
                raise ValidationError(
                    f'{self.name} must be one of: {", ".join(valid_values)}'
                )

        elif self.field_type == FieldType.MULTISELECT:
            if not isinstance(value, list):
                raise ValidationError(f'{self.name} must be a list')
            options = self.config.get('options', [])
            valid_values = [opt['value'] for opt in options]
            for v in value:
                if v not in valid_values:
                    raise ValidationError(
                        f'Invalid value "{v}" in {self.name}. Must be one of: {", ".join(valid_values)}'
                    )

        elif self.field_type == FieldType.CHECKBOX:
            if not isinstance(value, bool):
                raise ValidationError(f'{self.name} must be a boolean')

        elif self.field_type == FieldType.USER:
            # Value should be user ID (UUID string)
            if not isinstance(value, str):
                raise ValidationError(f'{self.name} must be a user ID')

        elif self.field_type == FieldType.URL:
            if not isinstance(value, str):
                raise ValidationError(f'{self.name} must be a URL string')
            # Basic URL validation
            if not value.startswith(('http://', 'https://')):
                raise ValidationError(f'{self.name} must be a valid URL')

        elif self.field_type == FieldType.EMAIL:
            if not isinstance(value, str):
                raise ValidationError(f'{self.name} must be an email string')
            # Basic email validation
            if '@' not in value:
                raise ValidationError(f'{self.name} must be a valid email')

        elif self.field_type == FieldType.LABELS:
            if not isinstance(value, list):
                raise ValidationError(f'{self.name} must be a list of labels')

    def get_render_config(self):
        """
        Get rendering configuration for frontend.

        Returns:
            Dict with rendering information
        """
        return {
            'id': str(self.id),
            'name': self.name,
            'field_type': self.field_type,
            'placeholder': self.placeholder,
            'help_text': self.help_text,
            'is_required': self.is_required,
            'default_value': self.default_value,
            'config': self.config,
        }


class FieldContext(BaseModel, AuditMixin):
    """
    Context for where a field should be displayed.

    Fields can be scoped to specific projects or issue types.
    """

    field = models.ForeignKey(
        FieldDefinition,
        on_delete=models.CASCADE,
        related_name='contexts',
        help_text=_('Field definition')
    )

    # Project scope (null = all projects in org)
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='field_contexts',
        null=True,
        blank=True,
        help_text=_('Project this context applies to (null for all projects)')
    )

    # Issue type scope (null = all issue types)
    issue_type = models.ForeignKey(
        'issues.IssueType',
        on_delete=models.CASCADE,
        related_name='field_contexts',
        null=True,
        blank=True,
        help_text=_('Issue type this context applies to (null for all types)')
    )

    # Context-specific overrides
    is_required = models.BooleanField(
        _('is required'),
        null=True,
        blank=True,
        help_text=_('Override field required setting in this context')
    )

    is_visible = models.BooleanField(
        _('is visible'),
        default=True,
        help_text=_('Whether field is visible in this context')
    )

    position = models.PositiveIntegerField(
        _('position'),
        default=0,
        help_text=_('Display order in this context')
    )

    class Meta:
        db_table = 'field_contexts'
        verbose_name = _('field context')
        verbose_name_plural = _('field contexts')
        ordering = ['field', 'project', 'issue_type', 'position']
        unique_together = [['field', 'project', 'issue_type']]
        indexes = [
            models.Index(fields=['field', 'project']),
            models.Index(fields=['field', 'issue_type']),
            models.Index(fields=['project', 'is_visible']),
        ]

    def __str__(self):
        """String representation."""
        scope = []
        if self.project:
            scope.append(f'Project: {self.project.key}')
        if self.issue_type:
            scope.append(f'Type: {self.issue_type.name}')
        scope_str = ', '.join(scope) if scope else 'Global'
        return f"{self.field.name} ({scope_str})"

    def get_effective_required(self):
        """
        Get effective required setting.

        Returns:
            Boolean
        """
        if self.is_required is not None:
            return self.is_required
        return self.field.is_required


class FieldScheme(BaseModel, AuditMixin):
    """
    Field scheme - collection of fields for a project.

    Similar to workflow schemes, allows grouping fields per project.
    """

    project = models.OneToOneField(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='field_scheme',
        help_text=_('Project this scheme belongs to')
    )

    name = models.CharField(
        _('name'),
        max_length=100,
        help_text=_('Scheme name')
    )

    description = models.TextField(
        _('description'),
        blank=True,
        help_text=_('Scheme description')
    )

    # Field configurations (JSONB)
    # Maps field_id to configuration overrides
    field_configs = models.JSONField(
        _('field configurations'),
        default=dict,
        blank=True,
        help_text=_('Field-specific configurations for this project')
    )

    is_active = models.BooleanField(
        _('is active'),
        default=True,
        help_text=_('Whether this scheme is active')
    )

    class Meta:
        db_table = 'field_schemes'
        verbose_name = _('field scheme')
        verbose_name_plural = _('field schemes')
        ordering = ['project']
        indexes = [
            models.Index(fields=['project', 'is_active']),
        ]

    def __str__(self):
        """String representation."""
        return f"{self.name} ({self.project.key})"

    def get_fields_for_issue_type(self, issue_type):
        """
        Get all fields applicable to a specific issue type.

        Args:
            issue_type: IssueType instance

        Returns:
            QuerySet of FieldDefinition instances
        """
        from django.db.models import Q

        # Get field contexts for this project and issue type
        contexts = FieldContext.objects.filter(
            Q(project=self.project) | Q(project__isnull=True),
            Q(issue_type=issue_type) | Q(issue_type__isnull=True),
            is_visible=True
        ).select_related('field')

        # Get unique fields
        field_ids = contexts.values_list('field_id', flat=True).distinct()

        return FieldDefinition.objects.filter(
            id__in=field_ids,
            is_active=True
        ).order_by('position')

    def get_field_config(self, field):
        """
        Get configuration for a specific field in this scheme.

        Args:
            field: FieldDefinition instance or ID

        Returns:
            Dict with field configuration
        """
        field_id = str(field.id) if hasattr(field, 'id') else str(field)

        if field_id in self.field_configs:
            return self.field_configs[field_id]

        return {}

    def set_field_config(self, field, config):
        """
        Set configuration for a specific field.

        Args:
            field: FieldDefinition instance or ID
            config: Configuration dict
        """
        field_id = str(field.id) if hasattr(field, 'id') else str(field)

        if not self.field_configs:
            self.field_configs = {}

        self.field_configs[field_id] = config
        self.save(update_fields=['field_configs', 'updated_at'])
