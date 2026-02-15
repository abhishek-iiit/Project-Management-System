"""
Issue-related actions for automation.
"""

from typing import Dict, Any
from django.core.exceptions import ValidationError
from .base import BaseAction


class UpdateFieldAction(BaseAction):
    """Action that updates a field value."""

    action_type = 'update_field'

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update field value.

        Args:
            context: Execution context with issue

        Returns:
            Execution result
        """
        issue = context.get('issue')
        if not issue:
            return {'success': False, 'error': 'No issue in context'}

        field = self.config.get('field')
        value = self.config.get('value')

        # Resolve smart values
        if isinstance(value, str):
            value = self.resolve_smart_values(value, context)

        try:
            # Update field
            if hasattr(issue, field):
                setattr(issue, field, value)
            else:
                # Update custom field
                issue.custom_field_values[field] = value

            issue.save()

            return {
                'success': True,
                'field': field,
                'value': value
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def validate_config(self) -> bool:
        """Validate configuration."""
        if 'field' not in self.config:
            raise ValidationError("update_field action requires 'field' in config")
        if 'value' not in self.config:
            raise ValidationError("update_field action requires 'value' in config")
        return True


class AssignToUserAction(BaseAction):
    """Action that assigns issue to a user."""

    action_type = 'assign_to_user'

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assign issue to user.

        Args:
            context: Execution context with issue

        Returns:
            Execution result
        """
        issue = context.get('issue')
        if not issue:
            return {'success': False, 'error': 'No issue in context'}

        user_expression = self.config.get('user')

        # Resolve smart values
        user_expression = self.resolve_smart_values(str(user_expression), context)

        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()

            # Handle special values
            if user_expression == 'reporter':
                user = issue.reporter
            elif user_expression == 'currentUser':
                user = context.get('user')
            else:
                # Try to find user by ID or email
                try:
                    user = User.objects.get(id=user_expression)
                except (User.DoesNotExist, ValueError):
                    try:
                        user = User.objects.get(email=user_expression)
                    except User.DoesNotExist:
                        return {
                            'success': False,
                            'error': f'User not found: {user_expression}'
                        }

            issue.assignee = user
            issue.save(update_fields=['assignee', 'updated_at'])

            return {
                'success': True,
                'assignee': user.get_full_name() if user else None
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def validate_config(self) -> bool:
        """Validate configuration."""
        if 'user' not in self.config:
            raise ValidationError("assign_to_user action requires 'user' in config")
        return True


class TransitionIssueAction(BaseAction):
    """Action that transitions issue to a new status."""

    action_type = 'transition_issue'

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transition issue.

        Args:
            context: Execution context with issue

        Returns:
            Execution result
        """
        issue = context.get('issue')
        if not issue:
            return {'success': False, 'error': 'No issue in context'}

        status_id = self.config.get('status')

        try:
            from apps.workflows.models import Status

            # Get status
            status = Status.objects.get(id=status_id)

            # Update issue status
            issue.status = status
            issue.save(update_fields=['status', 'updated_at'])

            return {
                'success': True,
                'status': status.name
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def validate_config(self) -> bool:
        """Validate configuration."""
        if 'status' not in self.config:
            raise ValidationError("transition_issue action requires 'status' in config")
        return True


class AddCommentAction(BaseAction):
    """Action that adds a comment to an issue."""

    action_type = 'add_comment'

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add comment to issue.

        Args:
            context: Execution context with issue

        Returns:
            Execution result
        """
        issue = context.get('issue')
        if not issue:
            return {'success': False, 'error': 'No issue in context'}

        comment_body = self.config.get('body')

        # Resolve smart values
        comment_body = self.resolve_smart_values(comment_body, context)

        try:
            from apps.issues.models import Comment

            # Create comment
            # Use a system user or the triggering user
            user = context.get('user')
            if not user:
                # Use reporter as fallback
                user = issue.reporter

            comment = Comment.objects.create(
                issue=issue,
                user=user,
                body=comment_body,
                created_by=user,
                updated_by=user
            )

            return {
                'success': True,
                'comment_id': str(comment.id)
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def validate_config(self) -> bool:
        """Validate configuration."""
        if 'body' not in self.config:
            raise ValidationError("add_comment action requires 'body' in config")
        return True


class SendNotificationAction(BaseAction):
    """Action that sends a notification."""

    action_type = 'send_notification'

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send notification.

        Args:
            context: Execution context

        Returns:
            Execution result
        """
        issue = context.get('issue')
        if not issue:
            return {'success': False, 'error': 'No issue in context'}

        recipients = self.config.get('recipients', [])
        message = self.config.get('message', '')

        # Resolve smart values
        message = self.resolve_smart_values(message, context)

        try:
            # TODO: Implement notification service
            # For now, just return success
            # In Phase 10, this will integrate with the notification system

            return {
                'success': True,
                'recipients': recipients,
                'message': message
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def validate_config(self) -> bool:
        """Validate configuration."""
        if 'message' not in self.config:
            raise ValidationError("send_notification action requires 'message' in config")
        return True


class CreateLinkedIssueAction(BaseAction):
    """Action that creates a linked issue."""

    action_type = 'create_linked_issue'

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create linked issue.

        Args:
            context: Execution context

        Returns:
            Execution result
        """
        issue = context.get('issue')
        if not issue:
            return {'success': False, 'error': 'No issue in context'}

        summary = self.config.get('summary', '')
        description = self.config.get('description', '')
        issue_type_id = self.config.get('issue_type')
        link_type = self.config.get('link_type', 'relates to')

        # Resolve smart values
        summary = self.resolve_smart_values(summary, context)
        description = self.resolve_smart_values(description, context)

        try:
            from apps.issues.models import Issue, IssueType, IssueLink, IssueLinkType

            # Get issue type
            issue_type = IssueType.objects.get(id=issue_type_id)

            # Create new issue
            new_issue = Issue.objects.create(
                project=issue.project,
                issue_type=issue_type,
                summary=summary,
                description=description,
                reporter=issue.reporter,
                status=issue.status,  # Use same status or get initial status
                created_by=issue.created_by,
                updated_by=issue.updated_by
            )

            # Create link
            link_type_obj, _ = IssueLinkType.objects.get_or_create(
                organization=issue.project.organization,
                name=link_type,
                defaults={
                    'outward_description': link_type,
                    'inward_description': link_type
                }
            )

            IssueLink.objects.create(
                from_issue=issue,
                to_issue=new_issue,
                link_type=link_type_obj,
                created_by=issue.created_by,
                updated_by=issue.updated_by
            )

            return {
                'success': True,
                'created_issue_key': new_issue.key
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def validate_config(self) -> bool:
        """Validate configuration."""
        if 'summary' not in self.config:
            raise ValidationError("create_linked_issue action requires 'summary' in config")
        if 'issue_type' not in self.config:
            raise ValidationError("create_linked_issue action requires 'issue_type' in config")
        return True


# Action registry
ACTION_REGISTRY = {
    'update_field': UpdateFieldAction,
    'assign_to_user': AssignToUserAction,
    'transition_issue': TransitionIssueAction,
    'add_comment': AddCommentAction,
    'send_notification': SendNotificationAction,
    'create_linked_issue': CreateLinkedIssueAction,
}


def get_action(action_type: str, config: Dict[str, Any]) -> BaseAction:
    """
    Get action instance for the given type.

    Args:
        action_type: Action type
        config: Action configuration

    Returns:
        Action instance

    Raises:
        ValueError: If action type is not registered
    """
    action_class = ACTION_REGISTRY.get(action_type)
    if not action_class:
        raise ValueError(f"Unknown action type: {action_type}")

    return action_class(config)
