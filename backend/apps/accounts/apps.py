from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Accounts app configuration."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    verbose_name = 'Accounts'

    def ready(self):
        """Import signals when app is ready."""
        # Import signals here if needed
        pass
