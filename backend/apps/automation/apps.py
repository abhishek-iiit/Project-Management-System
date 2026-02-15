from django.apps import AppConfig


class AutomationConfig(AppConfig):
    """Automation app configuration."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.automation'
    verbose_name = 'Automation'

    def ready(self):
        """Import signals when app is ready."""
        # Import signals to register automation triggers
        from apps.automation import signals  # noqa
