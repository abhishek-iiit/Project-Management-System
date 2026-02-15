"""
Search app configuration.
"""

from django.apps import AppConfig


class SearchConfig(AppConfig):
    """Search app configuration."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.search'
    verbose_name = 'Search & Filters'

    def ready(self):
        """Import signal handlers when app is ready."""
        # Import signals to register them
        try:
            from . import signals  # noqa
        except ImportError:
            pass
