"""
Base service class for business logic.

Following CLAUDE.md best practices:
- Keep views thin, move business logic to services
- Services handle complex operations spanning multiple models
- All database operations should be in services or models
"""

from typing import Optional
from django.db import transaction
from django.contrib.auth import get_user_model

User = get_user_model()


class BaseService:
    """
    Base service class for all business logic services.

    Services should:
    - Encapsulate business logic
    - Handle transactions
    - Validate complex business rules
    - Orchestrate multiple model operations

    Usage:
        class IssueService(BaseService):
            def __init__(self, user):
                super().__init__(user)

            @transaction.atomic
            def create_issue_with_comments(self, data):
                # Business logic here
                pass
    """

    def __init__(self, user: Optional[User] = None):
        """
        Initialize service with user context.

        Args:
            user: The user performing the operation (for permissions, audit, etc.)
        """
        self.user = user
        self.organization = None

        # Set organization from user if available
        if user and hasattr(user, 'current_organization'):
            self.organization = user.current_organization

    def _validate_permissions(self, obj, permission: str) -> bool:
        """
        Validate user has permission on object.

        Args:
            obj: The object to check permissions for
            permission: Permission string (e.g., 'view_issue', 'edit_project')

        Returns:
            True if user has permission

        Raises:
            PermissionDenied: If user lacks permission
        """
        if not self.user:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Authentication required")

        # Implement permission checking logic
        # This will be extended with django-guardian
        return True

    def _get_tenant_context(self):
        """
        Get current tenant/organization context.

        Returns:
            Organization instance or None
        """
        return self.organization

    @transaction.atomic
    def _create_with_audit(self, model_class, data: dict, created_by_field: str = 'created_by'):
        """
        Create model instance with audit trail.

        Args:
            model_class: Model class to instantiate
            data: Data for model creation
            created_by_field: Field name for created_by (default: 'created_by')

        Returns:
            Created model instance
        """
        if self.user and hasattr(model_class, created_by_field):
            data[created_by_field] = self.user

        return model_class.objects.create(**data)

    @transaction.atomic
    def _update_with_audit(self, instance, data: dict, updated_by_field: str = 'updated_by'):
        """
        Update model instance with audit trail.

        Args:
            instance: Model instance to update
            data: Data to update
            updated_by_field: Field name for updated_by (default: 'updated_by')

        Returns:
            Updated model instance
        """
        for key, value in data.items():
            setattr(instance, key, value)

        if self.user and hasattr(instance, updated_by_field):
            setattr(instance, updated_by_field, self.user)

        instance.save()
        return instance

    def _bulk_create(self, model_class, data_list: list, batch_size: int = 100):
        """
        Bulk create instances efficiently.

        Args:
            model_class: Model class
            data_list: List of dictionaries with model data
            batch_size: Number of records per batch (default: 100)

        Returns:
            List of created instances
        """
        instances = [model_class(**data) for data in data_list]
        return model_class.objects.bulk_create(instances, batch_size=batch_size)

    def _bulk_update(self, instances: list, fields: list, batch_size: int = 100):
        """
        Bulk update instances efficiently.

        Args:
            instances: List of model instances to update
            fields: List of field names to update
            batch_size: Number of records per batch (default: 100)

        Returns:
            Number of updated records
        """
        if not instances:
            return 0

        model_class = instances[0].__class__
        return model_class.objects.bulk_update(instances, fields, batch_size=batch_size)
