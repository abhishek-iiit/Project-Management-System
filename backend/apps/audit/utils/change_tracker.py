"""
Utility for tracking field-level changes in models.
"""

from typing import Dict, Any, Optional, List
from django.db import models


class ChangeTracker:
    """Utility for detecting and tracking field changes in model instances."""

    @staticmethod
    def get_model_changes(
        instance: models.Model,
        old_instance: Optional[models.Model] = None,
        tracked_fields: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get changes between old and new instance.

        Args:
            instance: Current model instance
            old_instance: Previous model instance (if available)
            tracked_fields: List of fields to track (None = all fields)

        Returns:
            Dict of changes in format: {field: {'from': old_val, 'to': new_val}}
        """
        changes = {}

        if old_instance is None:
            # New instance - all fields are "changes"
            return ChangeTracker._get_initial_values(instance, tracked_fields)

        # Get list of fields to check
        if tracked_fields:
            fields_to_check = tracked_fields
        else:
            fields_to_check = [
                f.name for f in instance._meta.get_fields()
                if not f.many_to_many and not f.one_to_many
            ]

        for field_name in fields_to_check:
            try:
                old_value = getattr(old_instance, field_name, None)
                new_value = getattr(instance, field_name, None)

                # Convert model instances to IDs for comparison
                if isinstance(old_value, models.Model):
                    old_value = old_value.pk
                if isinstance(new_value, models.Model):
                    new_value = new_value.pk

                # Check if value changed
                if old_value != new_value:
                    changes[field_name] = {
                        'from': ChangeTracker._serialize_value(old_value),
                        'to': ChangeTracker._serialize_value(new_value),
                    }

            except (AttributeError, ValueError):
                # Field doesn't exist or can't be accessed
                continue

        return changes

    @staticmethod
    def _get_initial_values(
        instance: models.Model,
        tracked_fields: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get initial values for new instance.

        Args:
            instance: Model instance
            tracked_fields: Optional list of fields to include

        Returns:
            Dict of initial values
        """
        changes = {}

        if tracked_fields:
            fields_to_check = tracked_fields
        else:
            fields_to_check = [
                f.name for f in instance._meta.get_fields()
                if not f.many_to_many and not f.one_to_many
            ]

        for field_name in fields_to_check:
            try:
                value = getattr(instance, field_name, None)

                # Skip auto-generated fields
                if field_name in ['id', 'created_at', 'updated_at']:
                    continue

                # Convert model instances to IDs
                if isinstance(value, models.Model):
                    value = value.pk

                if value is not None:
                    changes[field_name] = {
                        'from': None,
                        'to': ChangeTracker._serialize_value(value),
                    }

            except (AttributeError, ValueError):
                continue

        return changes

    @staticmethod
    def _serialize_value(value: Any) -> Any:
        """
        Serialize value for JSON storage.

        Args:
            value: Value to serialize

        Returns:
            JSON-serializable value
        """
        if value is None:
            return None

        # Convert UUID to string
        if hasattr(value, 'hex'):
            return str(value)

        # Convert datetime to ISO format
        if hasattr(value, 'isoformat'):
            return value.isoformat()

        # Convert bytes to string
        if isinstance(value, bytes):
            return value.decode('utf-8', errors='ignore')

        # Handle querysets
        if isinstance(value, models.QuerySet):
            return [ChangeTracker._serialize_value(item) for item in value]

        # Return as-is for primitive types
        if isinstance(value, (str, int, float, bool, list, dict)):
            return value

        # Convert to string for other types
        return str(value)

    @staticmethod
    def track_m2m_changes(
        instance: models.Model,
        field_name: str,
        old_values: Optional[List[Any]] = None,
        new_values: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        """
        Track many-to-many field changes.

        Args:
            instance: Model instance
            field_name: Name of M2M field
            old_values: Previous values
            new_values: New values

        Returns:
            Dict with added and removed items
        """
        if old_values is None:
            old_values = []
        if new_values is None:
            new_values = []

        old_set = set(old_values)
        new_set = set(new_values)

        added = list(new_set - old_set)
        removed = list(old_set - new_set)

        if added or removed:
            return {
                field_name: {
                    'added': [ChangeTracker._serialize_value(v) for v in added],
                    'removed': [ChangeTracker._serialize_value(v) for v in removed],
                }
            }

        return {}

    @staticmethod
    def get_issue_changes(old_issue, new_issue) -> Dict[str, Dict[str, Any]]:
        """
        Get changes for Issue model with special handling.

        Args:
            old_issue: Previous issue state
            new_issue: New issue state

        Returns:
            Dict of changes
        """
        # Track specific fields for issues
        tracked_fields = [
            'summary',
            'description',
            'issue_type',
            'status',
            'priority',
            'assignee',
            'reporter',
            'epic',
            'parent',
            'story_points',
            'time_estimate',
            'due_date',
            'custom_field_values',
        ]

        changes = ChangeTracker.get_model_changes(
            new_issue,
            old_issue,
            tracked_fields
        )

        # Add human-readable names for foreign keys
        if 'status' in changes:
            if old_issue and old_issue.status:
                changes['status']['from_name'] = old_issue.status.name
            if new_issue.status:
                changes['status']['to_name'] = new_issue.status.name

        if 'assignee' in changes:
            if old_issue and old_issue.assignee:
                changes['assignee']['from_name'] = old_issue.assignee.email
            if new_issue.assignee:
                changes['assignee']['to_name'] = new_issue.assignee.email

        if 'priority' in changes:
            if old_issue and old_issue.priority:
                changes['priority']['from_name'] = old_issue.priority.name
            if new_issue.priority:
                changes['priority']['to_name'] = new_issue.priority.name

        return changes
