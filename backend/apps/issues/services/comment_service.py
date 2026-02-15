"""
Comment service for managing issue comments.

Following CLAUDE.md best practices:
- Business logic in services
- Transaction management
"""

from typing import Dict
from django.db import transaction
from django.core.exceptions import PermissionDenied
from apps.common.services import BaseService
from apps.issues.models import Comment, Issue


class CommentService(BaseService):
    """
    Comment management service.

    Handles:
    - Comment creation and updates
    - Mention extraction
    - Comment deletion
    """

    @transaction.atomic
    def create_comment(self, issue: Issue, data: Dict) -> Comment:
        """
        Create a comment on an issue.

        Args:
            issue: Issue instance
            data: Comment data
                - body: str

        Returns:
            Comment instance

        Raises:
            PermissionDenied: If user lacks permission
        """
        # Check permission
        if not self._can_comment_on_issue(issue):
            raise PermissionDenied("You don't have permission to comment on this issue")

        # Create comment
        comment = Comment.objects.create(
            issue=issue,
            user=self.user,
            body=data['body'],
            created_by=self.user
        )

        # Extract mentions
        comment.extract_mentions()

        # Auto-watch issue for commenter
        issue.add_watcher(self.user)

        # TODO: Send notifications to watchers and mentioned users (Phase 10)

        return comment

    @transaction.atomic
    def update_comment(self, comment: Comment, data: Dict) -> Comment:
        """
        Update a comment.

        Args:
            comment: Comment instance
            data: Data to update

        Returns:
            Updated Comment instance

        Raises:
            PermissionDenied: If user lacks permission
        """
        # Check permission (only comment author can edit)
        if not self._can_edit_comment(comment):
            raise PermissionDenied("You don't have permission to edit this comment")

        # Update body
        if 'body' in data:
            comment.body = data['body']
            comment.updated_by = self.user
            comment.save()

            # Re-extract mentions
            comment.extract_mentions()

        return comment

    @transaction.atomic
    def delete_comment(self, comment: Comment):
        """
        Delete a comment.

        Args:
            comment: Comment instance

        Raises:
            PermissionDenied: If user lacks permission
        """
        # Check permission
        if not self._can_delete_comment(comment):
            raise PermissionDenied("You don't have permission to delete this comment")

        # Soft delete
        comment.delete()

    # Permission helpers

    def _can_comment_on_issue(self, issue: Issue) -> bool:
        """Check if user can comment on issue."""
        return issue.project.has_member(self.user)

    def _can_edit_comment(self, comment: Comment) -> bool:
        """Check if user can edit comment."""
        # Only comment author can edit
        return comment.user == self.user

    def _can_delete_comment(self, comment: Comment) -> bool:
        """Check if user can delete comment."""
        # Comment author or project admin can delete
        if comment.user == self.user:
            return True

        return comment.issue.project.is_member_admin(self.user)
