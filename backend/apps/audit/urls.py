"""
Audit URLs.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.audit import views

app_name = 'audit'

# Create router
router = DefaultRouter()
router.register(r'audit-logs', views.AuditLogViewSet, basename='audit-log')

urlpatterns = [
    path('', include(router.urls)),
]
