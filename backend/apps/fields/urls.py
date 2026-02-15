"""
Field URLs.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.fields import views

app_name = 'fields'

# Create router
router = DefaultRouter()
router.register(r'field-definitions', views.FieldDefinitionViewSet, basename='field-definition')
router.register(r'field-contexts', views.FieldContextViewSet, basename='field-context')
router.register(r'field-schemes', views.FieldSchemeViewSet, basename='field-scheme')

urlpatterns = [
    path('', include(router.urls)),
]
