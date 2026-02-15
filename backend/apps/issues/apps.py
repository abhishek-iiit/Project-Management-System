from django.apps import AppConfig


class IssuesConfig(AppConfig):
    """Issues app configuration."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.issues'
    verbose_name = 'Issues'

    def ready(self):
        """Import signals when app is ready."""
        # Import signals here if needed
        pass
