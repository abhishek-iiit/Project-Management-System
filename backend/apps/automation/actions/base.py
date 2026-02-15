"""
Base action class for automation.
"""

from typing import Dict, Any
from abc import ABC, abstractmethod


class BaseAction(ABC):
    """
    Base class for automation actions.

    Actions are operations performed when automation rules trigger.
    """

    action_type: str = None

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize action.

        Args:
            config: Action configuration
        """
        self.config = config

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the action.

        Args:
            context: Execution context with issue, event, user, etc.

        Returns:
            Dictionary with execution result

        Raises:
            Exception: If action execution fails
        """
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate action configuration.

        Returns:
            Boolean indicating if configuration is valid

        Raises:
            ValidationError: If configuration is invalid
        """
        pass

    def get_display_text(self) -> str:
        """
        Get human-readable description of this action.

        Returns:
            String description
        """
        return f"{self.action_type}: {self.config}"

    def resolve_smart_values(self, text: str, context: Dict[str, Any]) -> str:
        """
        Resolve smart values in text.

        Args:
            text: Text with smart values (e.g., "{{issue.key}}")
            context: Execution context

        Returns:
            Text with resolved smart values
        """
        import re

        # Get issue from context
        issue = context.get('issue')
        if not issue:
            return text

        # Define smart value mappings
        smart_values = {
            'issue.key': issue.key if hasattr(issue, 'key') else str(issue.id),
            'issue.summary': getattr(issue, 'summary', ''),
            'issue.description': getattr(issue, 'description', ''),
            'issue.status': getattr(issue.status, 'name', '') if hasattr(issue, 'status') and issue.status else '',
            'issue.priority': getattr(issue.priority, 'name', '') if hasattr(issue, 'priority') and issue.priority else '',
            'issue.assignee': getattr(issue.assignee, 'get_full_name', lambda: '')() if hasattr(issue, 'assignee') and issue.assignee else '',
            'issue.assignee.email': getattr(issue.assignee, 'email', '') if hasattr(issue, 'assignee') and issue.assignee else '',
            'issue.reporter': getattr(issue.reporter, 'get_full_name', lambda: '')() if hasattr(issue, 'reporter') and issue.reporter else '',
            'issue.reporter.email': getattr(issue.reporter, 'email', '') if hasattr(issue, 'reporter') and issue.reporter else '',
            'project.key': getattr(issue.project, 'key', '') if hasattr(issue, 'project') else '',
            'project.name': getattr(issue.project, 'name', '') if hasattr(issue, 'project') else '',
            'project.lead': getattr(issue.project.lead, 'get_full_name', lambda: '')() if hasattr(issue, 'project') and hasattr(issue.project, 'lead') and issue.project.lead else '',
        }

        # Replace smart values
        for key, value in smart_values.items():
            pattern = r'\{\{' + re.escape(key) + r'\}\}'
            text = re.sub(pattern, str(value), text)

        return text
