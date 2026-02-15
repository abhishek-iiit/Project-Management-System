"""
Notification URLs.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.notifications import views

app_name = 'notifications'

# Create router
router = DefaultRouter()
router.register(r'notifications', views.NotificationViewSet, basename='notification')
router.register(r'notification-preferences', views.NotificationPreferenceViewSet, basename='notification-preference')

urlpatterns = [
    path('', include(router.urls)),
]
