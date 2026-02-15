"""
WebSocket consumer for real-time notifications.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for user notifications.

    Handles real-time notification delivery to connected users.
    """

    async def connect(self):
        """Handle WebSocket connection."""
        # Get user from scope (set by authentication middleware)
        self.user = self.scope['user']

        if self.user.is_anonymous:
            # Reject connection for anonymous users
            await self.close()
            return

        # Create unique group name for this user
        self.group_name = f"notifications_{self.user.id}"

        # Join user's notification group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        # Accept connection
        await self.accept()

        # Send initial data (unread count, recent notifications)
        await self.send_initial_data()

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if hasattr(self, 'group_name'):
            # Leave notification group
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """
        Handle incoming WebSocket messages from client.

        Supports commands like:
        - mark_read: Mark notification as read
        - mark_all_read: Mark all notifications as read
        """
        try:
            data = json.loads(text_data)
            command = data.get('command')

            if command == 'mark_read':
                notification_id = data.get('notification_id')
                await self.mark_notification_read(notification_id)

            elif command == 'mark_all_read':
                await self.mark_all_notifications_read()

            elif command == 'get_unread_count':
                await self.send_unread_count()

            elif command == 'ping':
                # Simple ping/pong for keep-alive
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }))

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))

    async def notification_message(self, event):
        """
        Send notification to WebSocket client.

        Called when a notification is sent to the user's group.
        """
        notification = event['notification']

        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': notification
        }))

    async def send_initial_data(self):
        """Send initial data when user connects."""
        unread_count = await self.get_unread_count()
        recent_notifications = await self.get_recent_notifications()

        await self.send(text_data=json.dumps({
            'type': 'initial_data',
            'unread_count': unread_count,
            'notifications': recent_notifications
        }))

    async def send_unread_count(self):
        """Send current unread count to client."""
        unread_count = await self.get_unread_count()

        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': unread_count
        }))

    @database_sync_to_async
    def get_unread_count(self):
        """Get count of unread notifications for user."""
        from apps.notifications.models import Notification
        return Notification.objects.for_user(self.user).unread().count()

    @database_sync_to_async
    def get_recent_notifications(self, limit=20):
        """Get recent notifications for user."""
        from apps.notifications.models import Notification
        from apps.notifications.serializers import NotificationSerializer

        notifications = Notification.objects.for_user(self.user).recent(limit=limit)
        serializer = NotificationSerializer(notifications, many=True)
        return serializer.data

    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark a specific notification as read."""
        from apps.notifications.models import Notification

        try:
            notification = Notification.objects.get(
                id=notification_id,
                recipient=self.user
            )
            notification.mark_as_read()

            # Send confirmation
            self.send(text_data=json.dumps({
                'type': 'notification_read',
                'notification_id': notification_id
            }))

            # Send updated unread count
            self.send_unread_count()

        except Notification.DoesNotExist:
            self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Notification not found'
            }))

    @database_sync_to_async
    def mark_all_notifications_read(self):
        """Mark all notifications as read for user."""
        from apps.notifications.models import Notification

        count = Notification.objects.for_user(self.user).unread().mark_all_read()

        # Send confirmation
        self.send(text_data=json.dumps({
            'type': 'all_notifications_read',
            'count': count
        }))

        # Send updated unread count (should be 0)
        self.send_unread_count()
