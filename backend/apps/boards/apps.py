from django.apps import AppConfig


class BoardsConfig(AppConfig):
    """Boards app configuration."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.boards'
    verbose_name = 'Boards'

    def ready(self):
        """Import signals when app is ready."""
        # Import signals here if needed
        pass
