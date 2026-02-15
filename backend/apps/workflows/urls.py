"""
URL configuration for workflows app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.workflows.views import (
    WorkflowViewSet,
    StatusViewSet,
    TransitionViewSet,
    WorkflowSchemeViewSet,
)

app_name = 'workflows'

router = DefaultRouter()
router.register(r'workflows', WorkflowViewSet, basename='workflow')
router.register(r'statuses', StatusViewSet, basename='status')
router.register(r'transitions', TransitionViewSet, basename='transition')
router.register(r'workflow-schemes', WorkflowSchemeViewSet, basename='workflow-scheme')

urlpatterns = [
    path('', include(router.urls)),
]
