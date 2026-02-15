"""
Event dispatcher for triggering webhooks.
"""

import logging
from typing import Dict, Any, Optional

from apps.webhooks.services.webhook_service import WebhookService

logger = logging.getLogger(__name__)


class EventDispatcher:
    """Dispatches events to webhooks."""

    @staticmethod
    def dispatch_issue_created(issue, actor):
        """
        Dispatch issue created event.

        Args:
            issue: Issue instance
            actor: User who created the issue
        """
        from apps.issues.serializers import IssueSerializer

        event_data = {
            'id': str(issue.id),
            'issue': IssueSerializer(issue).data,
            'actor': {
                'id': str(actor.id),
                'email': actor.email,
                'name': actor.get_full_name() or actor.email,
            },
        }

        WebhookService.broadcast_event(
            event_type='issue:created',
            event_data=event_data,
            organization=issue.project.organization,
            project=issue.project,
        )

    @staticmethod
    def dispatch_issue_updated(issue, changes: Dict[str, Any], actor):
        """
        Dispatch issue updated event.

        Args:
            issue: Issue instance
            changes: Dict of changes (field -> {old, new})
            actor: User who updated the issue
        """
        from apps.issues.serializers import IssueSerializer

        event_data = {
            'id': str(issue.id),
            'issue': IssueSerializer(issue).data,
            'changes': changes,
            'actor': {
                'id': str(actor.id),
                'email': actor.email,
                'name': actor.get_full_name() or actor.email,
            },
        }

        WebhookService.broadcast_event(
            event_type='issue:updated',
            event_data=event_data,
            organization=issue.project.organization,
            project=issue.project,
        )

    @staticmethod
    def dispatch_issue_deleted(issue_data: Dict[str, Any], organization, project, actor):
        """
        Dispatch issue deleted event.

        Args:
            issue_data: Issue data before deletion
            organization: Organization instance
            project: Project instance
            actor: User who deleted the issue
        """
        event_data = {
            'issue': issue_data,
            'actor': {
                'id': str(actor.id),
                'email': actor.email,
                'name': actor.get_full_name() or actor.email,
            },
        }

        WebhookService.broadcast_event(
            event_type='issue:deleted',
            event_data=event_data,
            organization=organization,
            project=project,
        )

    @staticmethod
    def dispatch_issue_transitioned(issue, from_status, to_status, actor):
        """
        Dispatch issue transitioned event.

        Args:
            issue: Issue instance
            from_status: Previous status
            to_status: New status
            actor: User who transitioned the issue
        """
        from apps.issues.serializers import IssueSerializer

        event_data = {
            'id': str(issue.id),
            'issue': IssueSerializer(issue).data,
            'transition': {
                'from': {
                    'id': str(from_status.id),
                    'name': from_status.name,
                },
                'to': {
                    'id': str(to_status.id),
                    'name': to_status.name,
                },
            },
            'actor': {
                'id': str(actor.id),
                'email': actor.email,
                'name': actor.get_full_name() or actor.email,
            },
        }

        WebhookService.broadcast_event(
            event_type='issue:transitioned',
            event_data=event_data,
            organization=issue.project.organization,
            project=issue.project,
        )

    @staticmethod
    def dispatch_issue_commented(issue, comment, actor):
        """
        Dispatch issue commented event.

        Args:
            issue: Issue instance
            comment: Comment instance
            actor: User who added the comment
        """
        from apps.issues.serializers import IssueSerializer

        event_data = {
            'id': str(issue.id),
            'issue': IssueSerializer(issue).data,
            'comment': {
                'id': str(comment.id),
                'body': comment.body,
                'created_at': comment.created_at.isoformat(),
            },
            'actor': {
                'id': str(actor.id),
                'email': actor.email,
                'name': actor.get_full_name() or actor.email,
            },
        }

        WebhookService.broadcast_event(
            event_type='issue:commented',
            event_data=event_data,
            organization=issue.project.organization,
            project=issue.project,
        )

    @staticmethod
    def dispatch_sprint_started(sprint, actor):
        """
        Dispatch sprint started event.

        Args:
            sprint: Sprint instance
            actor: User who started the sprint
        """
        event_data = {
            'id': str(sprint.id),
            'sprint': {
                'id': str(sprint.id),
                'name': sprint.name,
                'goal': sprint.goal,
                'start_date': sprint.start_date.isoformat() if sprint.start_date else None,
                'end_date': sprint.end_date.isoformat() if sprint.end_date else None,
            },
            'actor': {
                'id': str(actor.id),
                'email': actor.email,
                'name': actor.get_full_name() or actor.email,
            },
        }

        WebhookService.broadcast_event(
            event_type='sprint:started',
            event_data=event_data,
            organization=sprint.board.project.organization,
            project=sprint.board.project,
        )

    @staticmethod
    def dispatch_sprint_completed(sprint, actor):
        """
        Dispatch sprint completed event.

        Args:
            sprint: Sprint instance
            actor: User who completed the sprint
        """
        event_data = {
            'id': str(sprint.id),
            'sprint': {
                'id': str(sprint.id),
                'name': sprint.name,
                'goal': sprint.goal,
                'start_date': sprint.start_date.isoformat() if sprint.start_date else None,
                'end_date': sprint.end_date.isoformat() if sprint.end_date else None,
                'completed_points': sprint.calculate_completed_points(),
                'total_points': sprint.get_total_story_points(),
            },
            'actor': {
                'id': str(actor.id),
                'email': actor.email,
                'name': actor.get_full_name() or actor.email,
            },
        }

        WebhookService.broadcast_event(
            event_type='sprint:completed',
            event_data=event_data,
            organization=sprint.board.project.organization,
            project=sprint.board.project,
        )

    @staticmethod
    def dispatch_project_created(project, actor):
        """
        Dispatch project created event.

        Args:
            project: Project instance
            actor: User who created the project
        """
        event_data = {
            'id': str(project.id),
            'project': {
                'id': str(project.id),
                'key': project.key,
                'name': project.name,
                'description': project.description,
            },
            'actor': {
                'id': str(actor.id),
                'email': actor.email,
                'name': actor.get_full_name() or actor.email,
            },
        }

        WebhookService.broadcast_event(
            event_type='project:created',
            event_data=event_data,
            organization=project.organization,
            project=None,  # Project-level, but send to org-wide webhooks
        )

    @staticmethod
    def dispatch_automation_executed(rule, execution, issue):
        """
        Dispatch automation executed event.

        Args:
            rule: AutomationRule instance
            execution: AutomationExecution instance
            issue: Optional Issue instance
        """
        event_data = {
            'rule': {
                'id': str(rule.id),
                'name': rule.name,
                'trigger_type': rule.trigger_type,
            },
            'execution': {
                'id': str(execution.id),
                'status': execution.status,
                'conditions_passed': execution.conditions_passed,
            },
            'issue': {
                'id': str(issue.id),
                'key': issue.key,
                'summary': issue.summary,
            } if issue else None,
        }

        WebhookService.broadcast_event(
            event_type='automation:executed',
            event_data=event_data,
            organization=rule.organization,
            project=rule.project,
        )
