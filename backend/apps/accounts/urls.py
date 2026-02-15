"""
Authentication URL configuration.
"""

from django.urls import path
from apps.accounts import views

app_name = 'accounts'

urlpatterns = [
    # Authentication endpoints
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('refresh/', views.refresh_token, name='refresh-token'),
    path('logout/', views.logout, name='logout'),

    # User profile
    path('me/', views.me, name='me'),
    path('change-password/', views.change_password, name='change-password'),
    path('stats/', views.user_stats, name='user-stats'),
]
