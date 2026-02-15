"""
Organizations URL configuration.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.organizations import views

app_name = 'organizations'

# Router for ViewSets
router = DefaultRouter()
router.register(r'organizations', views.OrganizationViewSet, basename='organization')

urlpatterns = [
    # Router URLs (organizations CRUD + custom actions)
    path('', include(router.urls)),

    # Invitation endpoints
    path('invitations/accept/', views.InvitationViewSet.as_view({'post': 'accept_invitation'}), name='accept-invitation'),
]
