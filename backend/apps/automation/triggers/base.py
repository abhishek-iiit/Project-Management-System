"""
Base trigger class for automation.
"""

from typing import Dict, Any
from abc import ABC, abstractmethod


class BaseTrigger(ABC):
    """
    Base class for automation triggers.

    Triggers detect events that should activate automation rules.
    """

    trigger_type: str = None

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize trigger.

        Args:
            config: Trigger configuration
        """
        self.config = config

    @abstractmethod
    def should_trigger(self, event_data: Dict[str, Any]) -> bool:
        """
        Check if this trigger should activate for the given event.

        Args:
            event_data: Event data

        Returns:
            Boolean indicating if trigger should activate
        """
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate trigger configuration.

        Returns:
            Boolean indicating if configuration is valid

        Raises:
            ValidationError: If configuration is invalid
        """
        pass

    def get_trigger_context(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get trigger context for use in conditions and actions.

        Args:
            event_data: Event data

        Returns:
            Dictionary with trigger context
        """
        return {
            'event': event_data,
            'trigger_type': self.trigger_type,
            'trigger_config': self.config
        }
