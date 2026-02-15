"""
Issue service for issue management.

Following CLAUDE.md best practices:
- Business logic in services
- Transaction management
- Permission validation
"""

from typing import Dict, List, Optional
from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils import timezone
from apps.common.services import BaseService
from apps.issues.models import (
    Issue, IssueType, Priority, Label, IssueLink, IssueLinkType, Watcher
)


class IssueService(BaseService):
    """
    Issue management service.

    Handles:
    - Issue creation and updates
    - Issue transitions
    - Issue linking
    - Watchers management
    - Hierarchy management
    """

    @transaction.atomic
    def create_issue(self, project, data: Dict) -> Issue:
        """
        Create a new issue.

        Args:
            project: Project instance
            data: Issue data
                - summary: str
                - issue_type: IssueType instance
                - description: str (optional)
                - priority: Priority instance (optional)
                - assignee: User instance (optional)
                - epic: Issue instance (optional)
                - parent: Issue instance (optional)
                - custom_field_values: dict (optional)
                - labels: list (optional)

        Returns:
            Issue instance

        Raises:
            ValidationError: If validation fails
            PermissionDenied: If user lacks permission
        """
        # Check permission
        if not self._can_create_issue(project):
            raise PermissionDenied("You don't have permission to create issues in this project")

        # Get workflow and initial status
        initial_status = self._get_initial_status(project, data.get('issue_type'))
        if not initial_status:
            raise ValidationError({
                'status': 'No workflow configured for this project and issue type'
            })

        # Set defaults
        if 'reporter' not in data:
            data['reporter'] = self.user

        if 'status' not in data:
            data['status'] = initial_status

        # Extract M2M and nested data
        labels_data = data.pop('labels', [])
        watchers_data = data.pop('watchers', [])

        # Create issue
        issue = Issue.objects.create(
            project=project,
            created_by=self.user,
            **data
        )

        # Add labels
        if labels_data:
            issue.labels.set(labels_data)

        # Add watchers
        if watchers_data:
            for user in watchers_data:
                issue.add_watcher(user)

        # Auto-watch for reporter
        issue.add_watcher(self.user)

        return issue

    @transaction.atomic
    def update_issue(self, issue: Issue, data: Dict) -> Issue:
        """
        Update issue details.

        Args:
            issue: Issue instance
            data: Data to update

        Returns:
            Updated Issue instance

        Raises:
            PermissionDenied: If user lacks permission
        """
        # Check permission
        if not self._can_edit_issue(issue):
            raise PermissionDenied("You don't have permission to edit this issue")

        # Update allowed fields
        allowed_fields = [
            'summary', 'description', 'issue_type', 'priority',
            'assignee', 'epic', 'parent', 'due_date',
            'original_estimate', 'remaining_estimate',
            'custom_field_values'
        ]

        # Handle labels separately (M2M)
        if 'labels' in data:
            labels = data.pop('labels')
            issue.labels.set(labels)

        for field in allowed_fields:
            if field in data:
                setattr(issue, field, data[field])

        issue.updated_by = self.user
        issue.save()

        return issue

    @transaction.atomic
    def transition_issue(self, issue: Issue, transition, comment: str = None, data: Dict = None) -> Issue:
        """
        Transition issue to a new status.

        Args:
            issue: Issue instance
            transition: Transition instance
            comment: Optional comment
            data: Optional data for validators/post-functions

        Returns:
            Updated Issue instance

        Raises:
            ValidationError: If transition validation fails
            PermissionDenied: If user lacks permission
        """
        from apps.workflows.services import WorkflowEngine

        # Delegate to workflow engine
        engine = WorkflowEngine(user=self.user)
        updated_issue = engine.execute_transition(
            issue=issue,
            transition=transition,
            user=self.user,
            data=data or {},
            comment=comment
        )

        # Update resolution date if moved to Done
        if updated_issue.status.category == 'done' and not updated_issue.resolution_date:
            updated_issue.resolution_date = timezone.now()
            updated_issue.save(update_fields=['resolution_date'])

        return updated_issue

    @transaction.atomic
    def delete_issue(self, issue: Issue):
        """
        Soft delete an issue.

        Args:
            issue: Issue instance

        Raises:
            PermissionDenied: If user lacks permission
            ValidationError: If issue has dependencies
        """
        # Check permission
        if not self._can_delete_issue(issue):
            raise PermissionDenied("You don't have permission to delete this issue")

        # Check for subtasks
        if issue.subtasks.exists():
            raise ValidationError({
                'issue': 'Cannot delete issue with subtasks. Delete subtasks first.'
            })

        # Soft delete
        issue.delete()

    @transaction.atomic
    def add_link(self, from_issue: Issue, to_issue: Issue, link_type: IssueLinkType) -> IssueLink:
        """
        Add a link between two issues.

        Args:
            from_issue: Source issue
            to_issue: Target issue
            link_type: Type of relationship

        Returns:
            IssueLink instance

        Raises:
            ValidationError: If validation fails
            PermissionDenied: If user lacks permission
        """
        # Check permission
        if not self._can_link_issue(from_issue):
            raise PermissionDenied("You don't have permission to link issues")

        # Validate
        if from_issue == to_issue:
            raise ValidationError({'to_issue': 'Cannot link issue to itself'})

        if from_issue.project.organization != to_issue.project.organization:
            raise ValidationError({
                'to_issue': 'Can only link issues within the same organization'
            })

        # Check if link already exists
        if IssueLink.objects.filter(
            from_issue=from_issue,
            to_issue=to_issue,
            link_type=link_type
        ).exists():
            raise ValidationError({'to_issue': 'Link already exists'})

        # Create link
        link = IssueLink.objects.create(
            from_issue=from_issue,
            to_issue=to_issue,
            link_type=link_type,
            created_by=self.user
        )

        return link

    @transaction.atomic
    def remove_link(self, link: IssueLink):
        """
        Remove a link between issues.

        Args:
            link: IssueLink instance

        Raises:
            PermissionDenied: If user lacks permission
        """
        # Check permission
        if not self._can_link_issue(link.from_issue):
            raise PermissionDenied("You don't have permission to remove issue links")

        link.delete()

    def add_watcher(self, issue: Issue, user) -> Watcher:
        """
        Add a watcher to an issue.

        Args:
            issue: Issue instance
            user: User to add as watcher

        Returns:
            Watcher instance

        Raises:
            PermissionDenied: If user lacks permission
        """
        # Check permission
        if not self._can_view_issue(issue):
            raise PermissionDenied("You don't have permission to watch this issue")

        watcher, created = Watcher.objects.get_or_create(
            issue=issue,
            user=user
        )

        return watcher

    def remove_watcher(self, issue: Issue, user):
        """
        Remove a watcher from an issue.

        Args:
            issue: Issue instance
            user: User to remove

        Raises:
            PermissionDenied: If user lacks permission
        """
        # User can always remove themselves
        if user != self.user:
            if not self._can_edit_issue(issue):
                raise PermissionDenied("You don't have permission to remove watchers")

        Watcher.objects.filter(issue=issue, user=user).delete()

    @transaction.atomic
    def log_work(self, issue: Issue, time_spent: int, comment: str = None) -> Issue:
        """
        Log work time on an issue.

        Args:
            issue: Issue instance
            time_spent: Time spent in minutes
            comment: Optional work log comment

        Returns:
            Updated Issue instance

        Raises:
            PermissionDenied: If user lacks permission
            ValidationError: If time_spent is invalid
        """
        # Check permission
        if not self._can_edit_issue(issue):
            raise PermissionDenied("You don't have permission to log work")

        if time_spent <= 0:
            raise ValidationError({'time_spent': 'Time spent must be positive'})

        # Update time tracking
        issue.time_spent += time_spent

        if issue.remaining_estimate and issue.remaining_estimate >= time_spent:
            issue.remaining_estimate -= time_spent
        else:
            issue.remaining_estimate = 0

        issue.updated_by = self.user
        issue.save(update_fields=['time_spent', 'remaining_estimate', 'updated_by', 'updated_at'])

        # TODO: Create work log entry (future enhancement)

        return issue

    @transaction.atomic
    def bulk_update_issues(self, issues: List[Issue], data: Dict) -> List[Issue]:
        """
        Update multiple issues at once.

        Args:
            issues: List of Issue instances
            data: Data to update (limited fields)

        Returns:
            List of updated Issue instances

        Raises:
            PermissionDenied: If user lacks permission for any issue
        """
        # Check permissions for all issues
        for issue in issues:
            if not self._can_edit_issue(issue):
                raise PermissionDenied(
                    f"You don't have permission to edit issue {issue.key}"
                )

        # Allowed fields for bulk update
        allowed_fields = ['assignee', 'priority', 'labels', 'epic']

        # Update issues
        updated_issues = []
        for issue in issues:
            # Handle labels separately
            if 'labels' in data:
                issue.labels.set(data['labels'])

            # Update other fields
            for field in allowed_fields:
                if field in data and field != 'labels':
                    setattr(issue, field, data[field])

            issue.updated_by = self.user
            updated_issues.append(issue)

        # Bulk update
        if updated_issues:
            update_fields = [f for f in allowed_fields if f in data and f != 'labels']
            update_fields.extend(['updated_by', 'updated_at'])
            Issue.objects.bulk_update(
                updated_issues,
                fields=update_fields,
                batch_size=100
            )

        return updated_issues

    def get_issue_stats(self, issue: Issue) -> Dict:
        """
        Get issue statistics.

        Args:
            issue: Issue instance

        Returns:
            Dict with issue stats
        """
        return {
            'comments_count': issue.comments.count(),
            'attachments_count': issue.attachments.count(),
            'watchers_count': issue.watchers.count(),
            'subtasks_count': issue.subtasks.count(),
            'links_count': issue.outward_links.count() + issue.inward_links.count(),
            'time_spent': issue.time_spent,
            'remaining_estimate': issue.remaining_estimate,
        }

    # Permission helpers

    def _can_create_issue(self, project) -> bool:
        """Check if user can create issues in project."""
        return project.has_member(self.user)

    def _can_view_issue(self, issue: Issue) -> bool:
        """Check if user can view issue."""
        return issue.project.has_member(self.user)

    def _can_edit_issue(self, issue: Issue) -> bool:
        """Check if user can edit issue."""
        return issue.project.has_member(self.user)

    def _can_delete_issue(self, issue: Issue) -> bool:
        """Check if user can delete issue."""
        # Only project admins or issue reporter can delete
        if issue.reporter == self.user:
            return True

        return issue.project.is_member_admin(self.user)

    def _can_link_issue(self, issue: Issue) -> bool:
        """Check if user can link issues."""
        return self._can_edit_issue(issue)

    def _get_initial_status(self, project, issue_type):
        """Get initial status for issue based on workflow scheme."""
        from apps.workflows.models import WorkflowScheme

        try:
            scheme = WorkflowScheme.objects.get(project=project, is_active=True)
            workflow = scheme.get_workflow_for_issue_type(issue_type)
            return workflow.get_initial_status()
        except WorkflowScheme.DoesNotExist:
            return None
