"""
URL configuration for projects app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.projects.views import (
    ProjectViewSet,
    ProjectRoleViewSet,
    ProjectTemplateViewSet,
)

app_name = 'projects'

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'roles', ProjectRoleViewSet, basename='project-role')
router.register(r'templates', ProjectTemplateViewSet, basename='project-template')

urlpatterns = [
    path('', include(router.urls)),
]
