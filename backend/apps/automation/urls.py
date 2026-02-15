"""
Automation URLs.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.automation import views

app_name = 'automation'

# Create router
router = DefaultRouter()
router.register(r'automation-rules', views.AutomationRuleViewSet, basename='automation-rule')
router.register(r'automation-executions', views.AutomationExecutionViewSet, basename='automation-execution')

urlpatterns = [
    path('', include(router.urls)),
]
