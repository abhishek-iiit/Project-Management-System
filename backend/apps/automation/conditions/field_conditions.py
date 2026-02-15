"""
Field-related conditions for automation.
"""

from typing import Dict, Any
from django.core.exceptions import ValidationError
from .base import BaseCondition


class FieldEqualsCondition(BaseCondition):
    """Condition that checks if a field equals a specific value."""

    condition_type = 'field_equals'

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """
        Check if field equals value.

        Args:
            context: Execution context with issue

        Returns:
            Boolean indicating if condition passes
        """
        issue = context.get('issue')
        if not issue:
            return False

        field = self.config.get('field')
        expected_value = self.config.get('value')

        # Get field value
        if hasattr(issue, field):
            actual_value = getattr(issue, field)

            # Handle foreign key fields (compare IDs)
            if hasattr(actual_value, 'id'):
                actual_value = str(actual_value.id)

            # Handle UUID fields
            if hasattr(actual_value, 'hex'):
                actual_value = str(actual_value)

        else:
            # Check custom fields
            actual_value = issue.custom_field_values.get(field)

        return str(actual_value) == str(expected_value)

    def validate_config(self) -> bool:
        """Validate configuration."""
        if 'field' not in self.config:
            raise ValidationError("field_equals condition requires 'field' in config")
        if 'value' not in self.config:
            raise ValidationError("field_equals condition requires 'value' in config")
        return True


class FieldContainsCondition(BaseCondition):
    """Condition that checks if a field contains a specific value."""

    condition_type = 'field_contains'

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """
        Check if field contains value.

        Args:
            context: Execution context with issue

        Returns:
            Boolean indicating if condition passes
        """
        issue = context.get('issue')
        if not issue:
            return False

        field = self.config.get('field')
        search_value = self.config.get('value')

        # Get field value
        if hasattr(issue, field):
            actual_value = getattr(issue, field)
        else:
            actual_value = issue.custom_field_values.get(field)

        if actual_value is None:
            return False

        return str(search_value).lower() in str(actual_value).lower()

    def validate_config(self) -> bool:
        """Validate configuration."""
        if 'field' not in self.config:
            raise ValidationError("field_contains condition requires 'field' in config")
        if 'value' not in self.config:
            raise ValidationError("field_contains condition requires 'value' in config")
        return True


class IssueTypeIsCondition(BaseCondition):
    """Condition that checks if issue type matches."""

    condition_type = 'issue_type_is'

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """
        Check if issue type matches.

        Args:
            context: Execution context with issue

        Returns:
            Boolean indicating if condition passes
        """
        issue = context.get('issue')
        if not issue or not issue.issue_type:
            return False

        expected_type = self.config.get('issue_type')
        return str(issue.issue_type.id) == str(expected_type) or issue.issue_type.name == expected_type

    def validate_config(self) -> bool:
        """Validate configuration."""
        if 'issue_type' not in self.config:
            raise ValidationError("issue_type_is condition requires 'issue_type' in config")
        return True


class PriorityIsCondition(BaseCondition):
    """Condition that checks if priority matches."""

    condition_type = 'priority_is'

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """
        Check if priority matches.

        Args:
            context: Execution context with issue

        Returns:
            Boolean indicating if condition passes
        """
        issue = context.get('issue')
        if not issue or not issue.priority:
            return False

        expected_priority = self.config.get('priority')
        return str(issue.priority.id) == str(expected_priority) or issue.priority.name == expected_priority

    def validate_config(self) -> bool:
        """Validate configuration."""
        if 'priority' not in self.config:
            raise ValidationError("priority_is condition requires 'priority' in config")
        return True


class UserInRoleCondition(BaseCondition):
    """Condition that checks if user has a specific role."""

    condition_type = 'user_in_role'

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """
        Check if user is in role.

        Args:
            context: Execution context with user

        Returns:
            Boolean indicating if condition passes
        """
        user = context.get('user')
        if not user:
            return False

        role = self.config.get('role')

        # Check project roles
        issue = context.get('issue')
        if issue and issue.project:
            project_member = issue.project.members.filter(user=user).first()
            if project_member:
                return project_member.role.name == role

        return False

    def validate_config(self) -> bool:
        """Validate configuration."""
        if 'role' not in self.config:
            raise ValidationError("user_in_role condition requires 'role' in config")
        return True


class AssigneeIsCondition(BaseCondition):
    """Condition that checks if assignee matches."""

    condition_type = 'assignee_is'

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """
        Check if assignee matches.

        Args:
            context: Execution context with issue

        Returns:
            Boolean indicating if condition passes
        """
        issue = context.get('issue')
        if not issue:
            return False

        expected_assignee = self.config.get('assignee')

        # Handle special values
        if expected_assignee == 'currentUser':
            user = context.get('user')
            if not user or not issue.assignee:
                return False
            return issue.assignee.id == user.id

        if expected_assignee == 'empty':
            return issue.assignee is None

        # Handle specific user ID
        if not issue.assignee:
            return False

        return str(issue.assignee.id) == str(expected_assignee)

    def validate_config(self) -> bool:
        """Validate configuration."""
        if 'assignee' not in self.config:
            raise ValidationError("assignee_is condition requires 'assignee' in config")
        return True


# Condition registry
CONDITION_REGISTRY = {
    'field_equals': FieldEqualsCondition,
    'field_contains': FieldContainsCondition,
    'issue_type_is': IssueTypeIsCondition,
    'priority_is': PriorityIsCondition,
    'user_in_role': UserInRoleCondition,
    'assignee_is': AssigneeIsCondition,
}


def get_condition(condition_type: str, config: Dict[str, Any]) -> BaseCondition:
    """
    Get condition instance for the given type.

    Args:
        condition_type: Condition type
        config: Condition configuration

    Returns:
        Condition instance

    Raises:
        ValueError: If condition type is not registered
    """
    condition_class = CONDITION_REGISTRY.get(condition_type)
    if not condition_class:
        raise ValueError(f"Unknown condition type: {condition_type}")

    return condition_class(config)
