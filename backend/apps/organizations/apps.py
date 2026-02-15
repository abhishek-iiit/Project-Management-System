from django.apps import AppConfig


class OrganizationsConfig(AppConfig):
    """Organizations app configuration."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.organizations'
    verbose_name = 'Organizations'

    def ready(self):
        """Import signals when app is ready."""
        # Import signals here if needed
        pass
