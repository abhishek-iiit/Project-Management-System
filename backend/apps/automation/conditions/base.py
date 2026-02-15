"""
Base condition class for automation.
"""

from typing import Dict, Any
from abc import ABC, abstractmethod


class BaseCondition(ABC):
    """
    Base class for automation conditions.

    Conditions determine whether automation rules should execute.
    """

    condition_type: str = None

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize condition.

        Args:
            config: Condition configuration
        """
        self.config = config

    @abstractmethod
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """
        Evaluate the condition.

        Args:
            context: Execution context with issue, event, etc.

        Returns:
            Boolean indicating if condition passes
        """
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate condition configuration.

        Returns:
            Boolean indicating if configuration is valid

        Raises:
            ValidationError: If configuration is invalid
        """
        pass

    def get_display_text(self) -> str:
        """
        Get human-readable description of this condition.

        Returns:
            String description
        """
        return f"{self.condition_type}: {self.config}"
