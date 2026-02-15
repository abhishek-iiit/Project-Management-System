"""
WebSocket consumer for real-time issue updates.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class IssueConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time issue updates.

    Allows users to subscribe to specific issues and receive real-time updates.
    """

    async def connect(self):
        """Handle WebSocket connection."""
        # Get user from scope
        self.user = self.scope['user']

        if self.user.is_anonymous:
            await self.close()
            return

        # Get issue ID from URL route
        self.issue_id = self.scope['url_route']['kwargs']['issue_id']

        # Check if user has access to this issue
        has_access = await self.check_issue_access()
        if not has_access:
            await self.close()
            return

        # Create group name for this issue
        self.group_name = f"issue_{self.issue_id}"

        # Join issue group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        # Accept connection
        await self.accept()

        # Send initial issue data
        await self.send_issue_data()

        # Broadcast that user is viewing this issue (for presence)
        await self.broadcast_user_joined()

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if hasattr(self, 'group_name'):
            # Broadcast that user left
            await self.broadcast_user_left()

            # Leave issue group
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            command = data.get('command')

            if command == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }))

            elif command == 'typing':
                # Broadcast typing indicator
                await self.broadcast_typing(data.get('is_typing', False))

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))

    # Event handlers (called when messages are sent to the group)

    async def issue_updated(self, event):
        """Send issue update to client."""
        await self.send(text_data=json.dumps({
            'type': 'issue_updated',
            'issue': event['issue'],
            'changes': event.get('changes', {}),
            'updated_by': event.get('updated_by')
        }))

    async def issue_commented(self, event):
        """Send new comment to client."""
        await self.send(text_data=json.dumps({
            'type': 'comment_added',
            'comment': event['comment'],
            'issue_id': event['issue_id']
        }))

    async def issue_transitioned(self, event):
        """Send status transition to client."""
        await self.send(text_data=json.dumps({
            'type': 'issue_transitioned',
            'issue_id': event['issue_id'],
            'from_status': event['from_status'],
            'to_status': event['to_status'],
            'transitioned_by': event.get('transitioned_by')
        }))

    async def user_presence(self, event):
        """Send user presence update to client."""
        await self.send(text_data=json.dumps({
            'type': 'user_presence',
            'action': event['action'],  # 'joined' or 'left'
            'user': event['user']
        }))

    async def user_typing(self, event):
        """Send typing indicator to client."""
        # Don't send typing notification back to the user who is typing
        if event['user_id'] != str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'user_typing',
                'user': event['user'],
                'is_typing': event['is_typing']
            }))

    # Helper methods

    async def send_issue_data(self):
        """Send current issue data to client."""
        issue_data = await self.get_issue_data()

        if issue_data:
            await self.send(text_data=json.dumps({
                'type': 'issue_data',
                'issue': issue_data
            }))

    async def broadcast_user_joined(self):
        """Broadcast that user joined issue view."""
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'user_presence',
                'action': 'joined',
                'user': {
                    'id': str(self.user.id),
                    'email': self.user.email,
                    'name': self.user.get_full_name() or self.user.email
                }
            }
        )

    async def broadcast_user_left(self):
        """Broadcast that user left issue view."""
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'user_presence',
                'action': 'left',
                'user': {
                    'id': str(self.user.id),
                    'email': self.user.email,
                    'name': self.user.get_full_name() or self.user.email
                }
            }
        )

    async def broadcast_typing(self, is_typing: bool):
        """Broadcast typing indicator."""
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'user_typing',
                'user_id': str(self.user.id),
                'user': {
                    'id': str(self.user.id),
                    'email': self.user.email,
                    'name': self.user.get_full_name() or self.user.email
                },
                'is_typing': is_typing
            }
        )

    @database_sync_to_async
    def check_issue_access(self):
        """Check if user has access to view this issue."""
        from apps.issues.models import Issue

        try:
            issue = Issue.objects.select_related(
                'project', 'project__organization'
            ).get(id=self.issue_id)

            # Check if user is a member of the organization
            from apps.organizations.models import OrganizationMember
            is_member = OrganizationMember.objects.filter(
                organization=issue.project.organization,
                user=self.user
            ).exists()

            return is_member

        except Issue.DoesNotExist:
            return False

    @database_sync_to_async
    def get_issue_data(self):
        """Get issue data for initial load."""
        from apps.issues.models import Issue
        from apps.issues.serializers import IssueSerializer

        try:
            issue = Issue.objects.select_related(
                'project',
                'issue_type',
                'status',
                'priority',
                'reporter',
                'assignee',
            ).prefetch_related(
                'labels',
                'watchers',
            ).get(id=self.issue_id)

            serializer = IssueSerializer(issue)
            return serializer.data

        except Issue.DoesNotExist:
            return None


# Helper function to broadcast issue updates
def broadcast_issue_update(issue, changes, updated_by):
    """
    Broadcast issue update to all connected clients.

    Args:
        issue: Issue instance
        changes: Dict of changes
        updated_by: User who made the update
    """
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    from apps.issues.serializers import IssueSerializer

    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    # Serialize issue
    serializer = IssueSerializer(issue)

    # Send to issue group
    async_to_sync(channel_layer.group_send)(
        f"issue_{issue.id}",
        {
            'type': 'issue_updated',
            'issue': serializer.data,
            'changes': changes,
            'updated_by': {
                'id': str(updated_by.id),
                'email': updated_by.email,
                'name': updated_by.get_full_name() or updated_by.email
            } if updated_by else None
        }
    )


def broadcast_comment_added(issue, comment, user):
    """
    Broadcast new comment to all connected clients.

    Args:
        issue: Issue instance
        comment: Comment instance
        user: User who added the comment
    """
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    async_to_sync(channel_layer.group_send)(
        f"issue_{issue.id}",
        {
            'type': 'issue_commented',
            'issue_id': str(issue.id),
            'comment': {
                'id': str(comment.id),
                'body': comment.body,
                'created_by': {
                    'id': str(user.id),
                    'email': user.email,
                    'name': user.get_full_name() or user.email
                },
                'created_at': comment.created_at.isoformat()
            }
        }
    )
