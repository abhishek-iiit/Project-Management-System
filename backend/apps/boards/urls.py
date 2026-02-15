"""
Board URLs.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.boards import views

app_name = 'boards'

# Create router
router = DefaultRouter()
router.register(r'boards', views.BoardViewSet, basename='board')
router.register(r'sprints', views.SprintViewSet, basename='sprint')

urlpatterns = [
    path('', include(router.urls)),
]
