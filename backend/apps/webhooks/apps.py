"""
Webhooks app configuration.
"""

from django.apps import AppConfig


class WebhooksConfig(AppConfig):
    """Webhooks app configuration."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.webhooks'
    verbose_name = 'Webhooks'
