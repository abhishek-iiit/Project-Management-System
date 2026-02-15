from django.apps import AppConfig


class CommonConfig(AppConfig):
    """Common app configuration."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.common'
    verbose_name = 'Common'

    def ready(self):
        """Import signals when app is ready."""
        # Import signals here if needed
        pass
