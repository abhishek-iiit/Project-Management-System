"""
Webhook URLs.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.webhooks import views

app_name = 'webhooks'

# Create router
router = DefaultRouter()
router.register(r'webhooks', views.WebhookViewSet, basename='webhook')
router.register(r'webhook-deliveries', views.WebhookDeliveryViewSet, basename='webhook-delivery')

urlpatterns = [
    path('', include(router.urls)),
]
