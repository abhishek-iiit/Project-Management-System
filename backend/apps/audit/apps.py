"""
Audit app configuration.
"""

from django.apps import AppConfig


class AuditConfig(AppConfig):
    """Audit app configuration."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.audit'
    verbose_name = 'Audit Logs'

    def ready(self):
        """Import signal handlers when app is ready."""
        try:
            from . import signals  # noqa
        except ImportError:
            pass
