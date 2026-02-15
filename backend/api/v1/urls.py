"""
API v1 URL configuration.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Initialize router
router = DefaultRouter()

# App URLs will be registered here as we build them
# Example:
# from apps.issues.views import IssueViewSet
# router.register(r'issues', IssueViewSet, basename='issue')

urlpatterns = [
    # Auth endpoints
    path('auth/', include('apps.accounts.urls')),

    # Organization endpoints
    path('', include('apps.organizations.urls')),

    # Project endpoints
    path('', include('apps.projects.urls')),

    # Workflow endpoints
    path('', include('apps.workflows.urls')),

    # Issue endpoints
    path('', include('apps.issues.urls')),

    # Field endpoints
    path('', include('apps.fields.urls')),

    # Board endpoints
    path('', include('apps.boards.urls')),

    # Automation endpoints
    path('', include('apps.automation.urls')),

    # Search endpoints
    path('', include('apps.search.urls')),

    # Notification endpoints
    path('', include('apps.notifications.urls')),

    # Webhook endpoints
    path('', include('apps.webhooks.urls')),

    # Audit endpoints
    path('', include('apps.audit.urls')),

    # Router URLs
    path('', include(router.urls)),
]
