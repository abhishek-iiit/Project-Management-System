"""
Notification service for creating and managing notifications.
"""

import re
from typing import List, Optional, Dict, Any
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.notifications.models import (
    Notification,
    NotificationType,
    NotificationPreference,
    NotificationChannel,
)

User = get_user_model()


class NotificationService:
    """Service for creating and sending notifications."""

    def __init__(self, organization):
        """
        Initialize notification service.

        Args:
            organization: Organization instance
        """
        self.organization = organization

    @transaction.atomic
    def create_notification(
        self,
        recipient: User,
        notification_type: str,
        title: str,
        message: str,
        actor: Optional[User] = None,
        issue=None,
        project=None,
        sprint=None,
        data: Optional[Dict] = None,
        action_url: str = '',
        send_email: bool = True,
    ) -> Notification:
        """
        Create a new notification.

        Args:
            recipient: User who will receive the notification
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            actor: User who triggered the notification
            issue: Related issue
            project: Related project
            sprint: Related sprint
            data: Additional data
            action_url: URL for deep linking
            send_email: Whether to send email notification

        Returns:
            Created Notification instance
        """
        # Check user preferences
        preference = NotificationPreference.get_or_create_for_user(
            user=recipient,
            organization=self.organization,
            project=project,
        )

        # Don't create notification if disabled
        if not preference.is_channel_enabled(NotificationChannel.IN_APP):
            return None

        if not preference.is_event_enabled(notification_type, NotificationChannel.IN_APP):
            return None

        # Create notification
        notification = Notification.objects.create(
            organization=self.organization,
            recipient=recipient,
            actor=actor,
            notification_type=notification_type,
            title=title,
            message=message,
            issue=issue,
            project=project,
            sprint=sprint,
            data=data or {},
            action_url=action_url,
        )

        # Send email if requested and enabled
        if send_email and preference.is_channel_enabled(NotificationChannel.EMAIL):
            if preference.is_event_enabled(notification_type, NotificationChannel.EMAIL):
                self._queue_email_notification(notification)

        # Send real-time notification via WebSocket
        self._send_realtime_notification(notification)

        return notification

    def notify_issue_created(self, issue, actor: User, watchers: Optional[List[User]] = None):
        """
        Notify users when an issue is created.

        Args:
            issue: Created issue
            actor: User who created the issue
            watchers: Optional list of users to notify
        """
        recipients = set()

        # Notify assignee
        if issue.assignee and issue.assignee != actor:
            recipients.add(issue.assignee)

        # Notify watchers
        if watchers:
            recipients.update([w for w in watchers if w != actor])

        # Notify project members (optional - can be configured)
        # project_members = issue.project.members.exclude(id=actor.id)
        # recipients.update(project_members)

        for recipient in recipients:
            self.create_notification(
                recipient=recipient,
                notification_type=NotificationType.ISSUE_CREATED,
                title=f"New issue: {issue.key}",
                message=f"{actor.get_full_name() or actor.email} created issue {issue.key} - {issue.summary}",
                actor=actor,
                issue=issue,
                project=issue.project,
                action_url=f"/projects/{issue.project.key}/issues/{issue.key}",
            )

    def notify_issue_assigned(self, issue, actor: User, previous_assignee: Optional[User] = None):
        """
        Notify user when an issue is assigned to them.

        Args:
            issue: Issue that was assigned
            actor: User who assigned the issue
            previous_assignee: Previous assignee (if any)
        """
        # Notify new assignee
        if issue.assignee and issue.assignee != actor:
            self.create_notification(
                recipient=issue.assignee,
                notification_type=NotificationType.ISSUE_ASSIGNED,
                title=f"Assigned to you: {issue.key}",
                message=f"{actor.get_full_name() or actor.email} assigned you to {issue.key} - {issue.summary}",
                actor=actor,
                issue=issue,
                project=issue.project,
                data={'previous_assignee': previous_assignee.email if previous_assignee else None},
                action_url=f"/projects/{issue.project.key}/issues/{issue.key}",
            )

    def notify_issue_commented(self, issue, comment, actor: User):
        """
        Notify users when a comment is added to an issue.

        Args:
            issue: Issue that was commented on
            comment: Comment that was added
            actor: User who added the comment
        """
        recipients = set()

        # Notify assignee
        if issue.assignee and issue.assignee != actor:
            recipients.add(issue.assignee)

        # Notify reporter
        if issue.reporter and issue.reporter != actor:
            recipients.add(issue.reporter)

        # Notify watchers
        watchers = issue.watchers.exclude(id=actor.id)
        recipients.update(watchers)

        # Check for mentions
        mentioned_users = self._extract_mentions(comment.body)
        recipients.update(mentioned_users)

        for recipient in recipients:
            # Different notification type for mentions
            if recipient in mentioned_users:
                notification_type = NotificationType.ISSUE_MENTIONED
                title = f"Mentioned in {issue.key}"
                message = f"{actor.get_full_name() or actor.email} mentioned you in {issue.key}"
            else:
                notification_type = NotificationType.ISSUE_COMMENTED
                title = f"New comment on {issue.key}"
                message = f"{actor.get_full_name() or actor.email} commented on {issue.key}"

            self.create_notification(
                recipient=recipient,
                notification_type=notification_type,
                title=title,
                message=message,
                actor=actor,
                issue=issue,
                project=issue.project,
                data={'comment_id': str(comment.id)},
                action_url=f"/projects/{issue.project.key}/issues/{issue.key}#comment-{comment.id}",
            )

    def notify_issue_transitioned(self, issue, actor: User, from_status, to_status):
        """
        Notify users when an issue status changes.

        Args:
            issue: Issue that was transitioned
            actor: User who transitioned the issue
            from_status: Previous status
            to_status: New status
        """
        recipients = set()

        # Notify assignee
        if issue.assignee and issue.assignee != actor:
            recipients.add(issue.assignee)

        # Notify reporter
        if issue.reporter and issue.reporter != actor:
            recipients.add(issue.reporter)

        # Notify watchers
        watchers = issue.watchers.exclude(id=actor.id)
        recipients.update(watchers)

        for recipient in recipients:
            self.create_notification(
                recipient=recipient,
                notification_type=NotificationType.ISSUE_TRANSITIONED,
                title=f"{issue.key} status changed",
                message=f"{actor.get_full_name() or actor.email} moved {issue.key} from {from_status.name} to {to_status.name}",
                actor=actor,
                issue=issue,
                project=issue.project,
                data={
                    'from_status': from_status.name,
                    'to_status': to_status.name,
                },
                action_url=f"/projects/{issue.project.key}/issues/{issue.key}",
            )

    def notify_sprint_started(self, sprint, actor: User):
        """
        Notify users when a sprint starts.

        Args:
            sprint: Sprint that was started
            actor: User who started the sprint
        """
        # Get all users with issues in the sprint
        issue_assignees = set()
        for issue in sprint.issues.all():
            if issue.assignee:
                issue_assignees.add(issue.assignee)

        for recipient in issue_assignees:
            if recipient != actor:
                self.create_notification(
                    recipient=recipient,
                    notification_type=NotificationType.SPRINT_STARTED,
                    title=f"Sprint started: {sprint.name}",
                    message=f"{actor.get_full_name() or actor.email} started sprint '{sprint.name}'",
                    actor=actor,
                    sprint=sprint,
                    project=sprint.board.project,
                    action_url=f"/boards/{sprint.board.id}/sprints/{sprint.id}",
                )

    def notify_sprint_completed(self, sprint, actor: User):
        """
        Notify users when a sprint is completed.

        Args:
            sprint: Sprint that was completed
            actor: User who completed the sprint
        """
        # Get all users with issues in the sprint
        issue_assignees = set()
        for issue in sprint.issues.all():
            if issue.assignee:
                issue_assignees.add(issue.assignee)

        completed_points = sprint.calculate_completed_points()
        total_points = sprint.get_total_story_points()

        for recipient in issue_assignees:
            if recipient != actor:
                self.create_notification(
                    recipient=recipient,
                    notification_type=NotificationType.SPRINT_COMPLETED,
                    title=f"Sprint completed: {sprint.name}",
                    message=f"Sprint '{sprint.name}' has been completed. {completed_points}/{total_points} story points completed.",
                    actor=actor,
                    sprint=sprint,
                    project=sprint.board.project,
                    data={
                        'completed_points': completed_points,
                        'total_points': total_points,
                    },
                    action_url=f"/boards/{sprint.board.id}/sprints/{sprint.id}/report",
                )

    def mark_as_read(self, notification_id: str, user: User) -> bool:
        """
        Mark a notification as read.

        Args:
            notification_id: Notification ID
            user: User marking the notification

        Returns:
            True if successful, False otherwise
        """
        try:
            notification = Notification.objects.get(
                id=notification_id,
                recipient=user,
            )
            notification.mark_as_read()
            return True
        except Notification.DoesNotExist:
            return False

    def mark_all_as_read(self, user: User) -> int:
        """
        Mark all notifications as read for a user.

        Args:
            user: User to mark notifications for

        Returns:
            Number of notifications marked as read
        """
        count = Notification.objects.for_user(user).for_organization(
            self.organization
        ).unread().mark_all_read()
        return count

    def get_unread_count(self, user: User) -> int:
        """
        Get count of unread notifications for a user.

        Args:
            user: User to count notifications for

        Returns:
            Number of unread notifications
        """
        return Notification.objects.for_user(user).for_organization(
            self.organization
        ).unread().count()

    def _extract_mentions(self, text: str) -> List[User]:
        """
        Extract mentioned users from text.

        Args:
            text: Text to extract mentions from

        Returns:
            List of mentioned User instances
        """
        # Extract @mentions (e.g., @user@example.com or @username)
        mention_pattern = r'@([\w\.-]+@[\w\.-]+|[\w]+)'
        mentions = re.findall(mention_pattern, text)

        users = []
        for mention in mentions:
            # Try to find user by email
            if '@' in mention:
                try:
                    user = User.objects.get(email=mention)
                    users.append(user)
                except User.DoesNotExist:
                    pass
            else:
                # Try to find by username or email prefix
                try:
                    user = User.objects.get(email__istartswith=mention)
                    users.append(user)
                except (User.DoesNotExist, User.MultipleObjectsReturned):
                    pass

        return users

    def _queue_email_notification(self, notification: Notification):
        """
        Queue email notification for async sending.

        Args:
            notification: Notification to send via email
        """
        # Import here to avoid circular imports
        try:
            from apps.notifications.tasks import send_notification_email
            send_notification_email.delay(str(notification.id))
        except ImportError:
            # Celery not configured, skip async task
            pass

    def _send_realtime_notification(self, notification: Notification):
        """
        Send real-time notification via WebSocket.

        Args:
            notification: Notification to send
        """
        # Import here to avoid circular imports
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync

            channel_layer = get_channel_layer()
            if channel_layer:
                # Send to user's notification channel
                async_to_sync(channel_layer.group_send)(
                    f"notifications_{notification.recipient.id}",
                    {
                        'type': 'notification_message',
                        'notification': {
                            'id': str(notification.id),
                            'type': notification.notification_type,
                            'title': notification.title,
                            'message': notification.message,
                            'action_url': notification.action_url,
                            'created_at': notification.created_at.isoformat(),
                        }
                    }
                )
        except Exception:
            # WebSocket not configured or failed, skip
            pass
