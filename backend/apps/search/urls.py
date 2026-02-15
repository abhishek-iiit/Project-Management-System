"""
Search URLs.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.search import views

app_name = 'search'

# Create router
router = DefaultRouter()
router.register(r'saved-filters', views.SavedFilterViewSet, basename='saved-filter')
router.register(r'search', views.SearchViewSet, basename='search')

urlpatterns = [
    path('', include(router.urls)),
]
