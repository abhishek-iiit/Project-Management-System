"""
Field service - business logic for custom fields.

Following CLAUDE.md best practices:
- Service layer for complex operations
- Transaction management
- Query optimization
"""

from typing import Dict, List, Optional
from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied
from django.contrib.auth import get_user_model
from apps.fields.models import FieldDefinition, FieldContext, FieldScheme
from apps.projects.models import Project
from apps.issues.models import IssueType

User = get_user_model()


class FieldService:
    """Service for custom field operations."""

    def __init__(self, user: User):
        """
        Initialize field service.

        Args:
            user: User performing operations
        """
        self.user = user
        self.organization = getattr(user, 'current_organization', None)

    def _check_organization_permission(self):
        """Check if user has organization access."""
        if not self.organization:
            raise PermissionDenied("No organization context available")

    def _check_field_permission(self, field: FieldDefinition):
        """Check if user can access field."""
        if field.organization_id != self.organization.id:
            raise PermissionDenied("Cannot access field from different organization")

    # ========================================
    # Field Definition Operations
    # ========================================

    @transaction.atomic
    def create_field_definition(self, data: Dict) -> FieldDefinition:
        """
        Create a new field definition.

        Args:
            data: Field definition data

        Returns:
            Created FieldDefinition instance

        Raises:
            PermissionDenied: If user lacks permissions
            ValidationError: If data is invalid
        """
        self._check_organization_permission()

        # Set organization
        data['organization'] = self.organization

        # Set audit fields
        data['created_by'] = self.user
        data['updated_by'] = self.user

        # Create field definition
        field = FieldDefinition(**data)
        field.full_clean()  # Validate
        field.save()

        return field

    def get_field_definition(self, field_id: str) -> FieldDefinition:
        """
        Get a field definition by ID.

        Args:
            field_id: Field UUID

        Returns:
            FieldDefinition instance

        Raises:
            PermissionDenied: If user lacks permissions
            FieldDefinition.DoesNotExist: If field not found
        """
        self._check_organization_permission()

        field = FieldDefinition.objects.get(id=field_id)
        self._check_field_permission(field)

        return field

    def list_field_definitions(
        self,
        is_active: Optional[bool] = None,
        field_type: Optional[str] = None
    ) -> List[FieldDefinition]:
        """
        List field definitions for organization.

        Args:
            is_active: Filter by active status
            field_type: Filter by field type

        Returns:
            List of FieldDefinition instances
        """
        self._check_organization_permission()

        queryset = FieldDefinition.objects.filter(
            organization=self.organization
        ).order_by('position', 'name')

        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        if field_type:
            queryset = queryset.filter(field_type=field_type)

        return list(queryset)

    @transaction.atomic
    def update_field_definition(
        self,
        field_id: str,
        data: Dict
    ) -> FieldDefinition:
        """
        Update a field definition.

        Args:
            field_id: Field UUID
            data: Update data

        Returns:
            Updated FieldDefinition instance

        Raises:
            PermissionDenied: If user lacks permissions
            ValidationError: If data is invalid
        """
        field = self.get_field_definition(field_id)

        # Update fields
        for key, value in data.items():
            if key not in ['id', 'organization', 'created_by', 'created_at']:
                setattr(field, key, value)

        # Set audit fields
        field.updated_by = self.user

        # Validate and save
        field.full_clean()
        field.save()

        return field

    @transaction.atomic
    def delete_field_definition(self, field_id: str) -> None:
        """
        Delete (soft delete) a field definition.

        Args:
            field_id: Field UUID

        Raises:
            PermissionDenied: If user lacks permissions
        """
        field = self.get_field_definition(field_id)
        field.delete()  # Soft delete via SoftDeleteModel

    @transaction.atomic
    def reorder_fields(self, field_order: List[str]) -> None:
        """
        Reorder field definitions.

        Args:
            field_order: List of field IDs in desired order

        Raises:
            PermissionDenied: If user lacks permissions
            ValidationError: If field IDs are invalid
        """
        self._check_organization_permission()

        # Validate all fields belong to organization
        fields = FieldDefinition.objects.filter(
            id__in=field_order,
            organization=self.organization
        )

        if fields.count() != len(field_order):
            raise ValidationError("Invalid field IDs provided")

        # Update positions
        for position, field_id in enumerate(field_order):
            FieldDefinition.objects.filter(id=field_id).update(position=position)

    def validate_field_value(
        self,
        field_id: str,
        value: any
    ) -> None:
        """
        Validate a value against a field definition.

        Args:
            field_id: Field UUID
            value: Value to validate

        Raises:
            ValidationError: If value is invalid
        """
        field = self.get_field_definition(field_id)
        field.validate_value(value)

    # ========================================
    # Field Context Operations
    # ========================================

    @transaction.atomic
    def create_field_context(self, data: Dict) -> FieldContext:
        """
        Create a field context (scope fields to projects/issue types).

        Args:
            data: Field context data

        Returns:
            Created FieldContext instance

        Raises:
            PermissionDenied: If user lacks permissions
            ValidationError: If data is invalid
        """
        self._check_organization_permission()

        # Validate field belongs to organization
        field = data.get('field')
        if isinstance(field, str):
            field = self.get_field_definition(field)
            data['field'] = field
        else:
            self._check_field_permission(field)

        # Set audit fields
        data['created_by'] = self.user
        data['updated_by'] = self.user

        # Create context
        context = FieldContext(**data)
        context.full_clean()
        context.save()

        return context

    def get_field_context(self, context_id: str) -> FieldContext:
        """
        Get a field context by ID.

        Args:
            context_id: Context UUID

        Returns:
            FieldContext instance

        Raises:
            PermissionDenied: If user lacks permissions
            FieldContext.DoesNotExist: If context not found
        """
        self._check_organization_permission()

        context = FieldContext.objects.select_related('field').get(id=context_id)
        self._check_field_permission(context.field)

        return context

    def list_field_contexts(
        self,
        field_id: Optional[str] = None,
        project_id: Optional[str] = None,
        issue_type_id: Optional[str] = None
    ) -> List[FieldContext]:
        """
        List field contexts.

        Args:
            field_id: Filter by field
            project_id: Filter by project
            issue_type_id: Filter by issue type

        Returns:
            List of FieldContext instances
        """
        self._check_organization_permission()

        queryset = FieldContext.objects.select_related(
            'field', 'project', 'issue_type'
        ).filter(
            field__organization=self.organization
        ).order_by('field', 'position')

        if field_id:
            queryset = queryset.filter(field_id=field_id)

        if project_id:
            queryset = queryset.filter(project_id=project_id)

        if issue_type_id:
            queryset = queryset.filter(issue_type_id=issue_type_id)

        return list(queryset)

    @transaction.atomic
    def update_field_context(
        self,
        context_id: str,
        data: Dict
    ) -> FieldContext:
        """
        Update a field context.

        Args:
            context_id: Context UUID
            data: Update data

        Returns:
            Updated FieldContext instance

        Raises:
            PermissionDenied: If user lacks permissions
            ValidationError: If data is invalid
        """
        context = self.get_field_context(context_id)

        # Update fields
        for key, value in data.items():
            if key not in ['id', 'field', 'created_by', 'created_at']:
                setattr(context, key, value)

        # Set audit fields
        context.updated_by = self.user

        # Validate and save
        context.full_clean()
        context.save()

        return context

    @transaction.atomic
    def delete_field_context(self, context_id: str) -> None:
        """
        Delete a field context.

        Args:
            context_id: Context UUID

        Raises:
            PermissionDenied: If user lacks permissions
        """
        context = self.get_field_context(context_id)
        context.delete()

    def get_fields_for_issue_type(
        self,
        project: Project,
        issue_type: IssueType
    ) -> List[FieldDefinition]:
        """
        Get all fields applicable to a specific project and issue type.

        Args:
            project: Project instance
            issue_type: IssueType instance

        Returns:
            List of FieldDefinition instances with context information
        """
        from django.db.models import Q

        # Get field contexts for this project and issue type
        contexts = FieldContext.objects.filter(
            Q(project=project) | Q(project__isnull=True),
            Q(issue_type=issue_type) | Q(issue_type__isnull=True),
            is_visible=True,
            field__organization=self.organization,
            field__is_active=True
        ).select_related('field').order_by('position')

        # Get unique fields
        field_ids = set(ctx.field_id for ctx in contexts)

        fields = FieldDefinition.objects.filter(
            id__in=field_ids
        ).order_by('position', 'name')

        return list(fields)

    # ========================================
    # Field Scheme Operations
    # ========================================

    @transaction.atomic
    def create_field_scheme(self, data: Dict) -> FieldScheme:
        """
        Create a field scheme for a project.

        Args:
            data: Field scheme data

        Returns:
            Created FieldScheme instance

        Raises:
            PermissionDenied: If user lacks permissions
            ValidationError: If data is invalid
        """
        self._check_organization_permission()

        # Validate project belongs to organization
        project = data.get('project')
        if isinstance(project, str):
            project = Project.objects.get(id=project)
            data['project'] = project

        if project.organization_id != self.organization.id:
            raise PermissionDenied("Cannot create scheme for project in different organization")

        # Set audit fields
        data['created_by'] = self.user
        data['updated_by'] = self.user

        # Create scheme
        scheme = FieldScheme(**data)
        scheme.full_clean()
        scheme.save()

        return scheme

    def get_field_scheme(self, scheme_id: str) -> FieldScheme:
        """
        Get a field scheme by ID.

        Args:
            scheme_id: Scheme UUID

        Returns:
            FieldScheme instance

        Raises:
            PermissionDenied: If user lacks permissions
            FieldScheme.DoesNotExist: If scheme not found
        """
        self._check_organization_permission()

        scheme = FieldScheme.objects.select_related('project').get(id=scheme_id)

        if scheme.project.organization_id != self.organization.id:
            raise PermissionDenied("Cannot access scheme from different organization")

        return scheme

    def get_field_scheme_for_project(self, project_id: str) -> Optional[FieldScheme]:
        """
        Get field scheme for a project.

        Args:
            project_id: Project UUID

        Returns:
            FieldScheme instance or None

        Raises:
            PermissionDenied: If user lacks permissions
        """
        self._check_organization_permission()

        try:
            scheme = FieldScheme.objects.select_related('project').get(
                project_id=project_id
            )

            if scheme.project.organization_id != self.organization.id:
                raise PermissionDenied("Cannot access scheme from different organization")

            return scheme
        except FieldScheme.DoesNotExist:
            return None

    @transaction.atomic
    def update_field_scheme(
        self,
        scheme_id: str,
        data: Dict
    ) -> FieldScheme:
        """
        Update a field scheme.

        Args:
            scheme_id: Scheme UUID
            data: Update data

        Returns:
            Updated FieldScheme instance

        Raises:
            PermissionDenied: If user lacks permissions
            ValidationError: If data is invalid
        """
        scheme = self.get_field_scheme(scheme_id)

        # Update fields
        for key, value in data.items():
            if key not in ['id', 'project', 'created_by', 'created_at']:
                setattr(scheme, key, value)

        # Set audit fields
        scheme.updated_by = self.user

        # Validate and save
        scheme.full_clean()
        scheme.save()

        return scheme

    @transaction.atomic
    def delete_field_scheme(self, scheme_id: str) -> None:
        """
        Delete a field scheme.

        Args:
            scheme_id: Scheme UUID

        Raises:
            PermissionDenied: If user lacks permissions
        """
        scheme = self.get_field_scheme(scheme_id)
        scheme.delete()

    @transaction.atomic
    def set_field_config_for_scheme(
        self,
        scheme_id: str,
        field_id: str,
        config: Dict
    ) -> FieldScheme:
        """
        Set configuration for a specific field in a scheme.

        Args:
            scheme_id: Scheme UUID
            field_id: Field UUID
            config: Field configuration

        Returns:
            Updated FieldScheme instance

        Raises:
            PermissionDenied: If user lacks permissions
            ValidationError: If field or scheme invalid
        """
        scheme = self.get_field_scheme(scheme_id)
        field = self.get_field_definition(field_id)

        # Set config
        scheme.set_field_config(field, config)

        return scheme

    def get_field_config_for_scheme(
        self,
        scheme_id: str,
        field_id: str
    ) -> Dict:
        """
        Get configuration for a specific field in a scheme.

        Args:
            scheme_id: Scheme UUID
            field_id: Field UUID

        Returns:
            Field configuration dict

        Raises:
            PermissionDenied: If user lacks permissions
        """
        scheme = self.get_field_scheme(scheme_id)
        return scheme.get_field_config(field_id)

    # ========================================
    # Bulk Operations
    # ========================================

    @transaction.atomic
    def bulk_create_field_contexts(
        self,
        field_id: str,
        contexts_data: List[Dict]
    ) -> List[FieldContext]:
        """
        Bulk create field contexts for a field.

        Args:
            field_id: Field UUID
            contexts_data: List of context data dicts

        Returns:
            List of created FieldContext instances

        Raises:
            PermissionDenied: If user lacks permissions
            ValidationError: If data is invalid
        """
        field = self.get_field_definition(field_id)

        contexts = []
        for data in contexts_data:
            data['field'] = field
            data['created_by'] = self.user
            data['updated_by'] = self.user
            context = FieldContext(**data)
            context.full_clean()
            contexts.append(context)

        # Bulk create
        created_contexts = FieldContext.objects.bulk_create(
            contexts,
            batch_size=100
        )

        return created_contexts

    @transaction.atomic
    def copy_field_contexts_to_project(
        self,
        source_project_id: str,
        target_project_id: str
    ) -> List[FieldContext]:
        """
        Copy field contexts from one project to another.

        Args:
            source_project_id: Source project UUID
            target_project_id: Target project UUID

        Returns:
            List of created FieldContext instances

        Raises:
            PermissionDenied: If user lacks permissions
        """
        self._check_organization_permission()

        # Get source contexts
        source_contexts = FieldContext.objects.filter(
            project_id=source_project_id,
            field__organization=self.organization
        ).select_related('field')

        # Create new contexts for target project
        new_contexts = []
        for ctx in source_contexts:
            new_context = FieldContext(
                field=ctx.field,
                project_id=target_project_id,
                issue_type=ctx.issue_type,
                is_required=ctx.is_required,
                is_visible=ctx.is_visible,
                position=ctx.position,
                created_by=self.user,
                updated_by=self.user
            )
            new_contexts.append(new_context)

        # Bulk create
        created_contexts = FieldContext.objects.bulk_create(
            new_contexts,
            batch_size=100
        )

        return created_contexts
