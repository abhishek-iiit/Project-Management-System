"""
WebSocket URL routing.
"""

from django.urls import re_path
from apps.notifications.consumers import NotificationConsumer, IssueConsumer

websocket_urlpatterns = [
    # User notifications
    re_path(r'ws/notifications/$', NotificationConsumer.as_asgi()),

    # Issue real-time updates
    re_path(r'ws/issues/(?P<issue_id>[0-9a-f-]+)/$', IssueConsumer.as_asgi()),
]
