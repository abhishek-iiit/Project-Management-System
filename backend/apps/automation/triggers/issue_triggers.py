"""
Issue-related triggers for automation.
"""

from typing import Dict, Any
from django.core.exceptions import ValidationError
from .base import BaseTrigger


class IssueCreatedTrigger(BaseTrigger):
    """Trigger when an issue is created."""

    trigger_type = 'issue_created'

    def should_trigger(self, event_data: Dict[str, Any]) -> bool:
        """Check if issue was created."""
        return event_data.get('event_type') == 'issue_created'

    def validate_config(self) -> bool:
        """Validate configuration (no config needed for this trigger)."""
        return True


class IssueUpdatedTrigger(BaseTrigger):
    """Trigger when an issue is updated."""

    trigger_type = 'issue_updated'

    def should_trigger(self, event_data: Dict[str, Any]) -> bool:
        """Check if issue was updated."""
        return event_data.get('event_type') == 'issue_updated'

    def validate_config(self) -> bool:
        """Validate configuration (no config needed for this trigger)."""
        return True


class FieldChangedTrigger(BaseTrigger):
    """Trigger when a specific field value changes."""

    trigger_type = 'field_changed'

    def should_trigger(self, event_data: Dict[str, Any]) -> bool:
        """Check if specified field changed."""
        if event_data.get('event_type') != 'issue_updated':
            return False

        field_name = self.config.get('field')
        if not field_name:
            return False

        changed_fields = event_data.get('changed_fields', [])
        return field_name in changed_fields

    def validate_config(self) -> bool:
        """Validate configuration."""
        if 'field' not in self.config:
            raise ValidationError("field_changed trigger requires 'field' in config")
        return True


class IssueTransitionedTrigger(BaseTrigger):
    """Trigger when an issue transitions (status changes)."""

    trigger_type = 'issue_transitioned'

    def should_trigger(self, event_data: Dict[str, Any]) -> bool:
        """Check if issue status changed."""
        if event_data.get('event_type') != 'issue_updated':
            return False

        changed_fields = event_data.get('changed_fields', [])
        return 'status' in changed_fields

    def validate_config(self) -> bool:
        """Validate configuration."""
        # Optional: can specify from_status and/or to_status
        return True


class IssueAssignedTrigger(BaseTrigger):
    """Trigger when an issue is assigned."""

    trigger_type = 'issue_assigned'

    def should_trigger(self, event_data: Dict[str, Any]) -> bool:
        """Check if issue was assigned."""
        if event_data.get('event_type') != 'issue_updated':
            return False

        changed_fields = event_data.get('changed_fields', [])
        if 'assignee' not in changed_fields:
            return False

        # Check if assignee was changed from None to a value (newly assigned)
        changes = event_data.get('changes', {})
        assignee_change = changes.get('assignee', {})
        old_value = assignee_change.get('old')
        new_value = assignee_change.get('new')

        return old_value is None and new_value is not None

    def validate_config(self) -> bool:
        """Validate configuration (no config needed for this trigger)."""
        return True


class CommentAddedTrigger(BaseTrigger):
    """Trigger when a comment is added to an issue."""

    trigger_type = 'comment_added'

    def should_trigger(self, event_data: Dict[str, Any]) -> bool:
        """Check if comment was added."""
        return event_data.get('event_type') == 'comment_added'

    def validate_config(self) -> bool:
        """Validate configuration (no config needed for this trigger)."""
        return True


# Trigger registry
TRIGGER_REGISTRY = {
    'issue_created': IssueCreatedTrigger,
    'issue_updated': IssueUpdatedTrigger,
    'field_changed': FieldChangedTrigger,
    'issue_transitioned': IssueTransitionedTrigger,
    'issue_assigned': IssueAssignedTrigger,
    'comment_added': CommentAddedTrigger,
}


def get_trigger(trigger_type: str, config: Dict[str, Any]) -> BaseTrigger:
    """
    Get trigger instance for the given type.

    Args:
        trigger_type: Trigger type
        config: Trigger configuration

    Returns:
        Trigger instance

    Raises:
        ValueError: If trigger type is not registered
    """
    trigger_class = TRIGGER_REGISTRY.get(trigger_type)
    if not trigger_class:
        raise ValueError(f"Unknown trigger type: {trigger_type}")

    return trigger_class(config)
