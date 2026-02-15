"""
Workflow engine for executing state transitions.

Following CLAUDE.md best practices:
- Business logic in services
- Transaction management
- Validation before execution
"""

from typing import Dict, List, Optional
from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied
from apps.common.services import BaseService
from apps.workflows.models import Workflow, Status, Transition, WorkflowScheme


class WorkflowEngine(BaseService):
    """
    Workflow engine for validating and executing transitions.

    Handles:
    - Transition validation
    - Condition checking
    - Validator execution
    - Post-function execution
    """

    def get_available_transitions(self, issue, user=None):
        """
        Get all available transitions for an issue.

        Args:
            issue: Issue instance
            user: Optional User instance for permission checks

        Returns:
            List of Transition instances
        """
        # Get workflow for issue
        workflow = self._get_workflow_for_issue(issue)

        if not workflow:
            return []

        # Get transitions from current status
        current_status = issue.status
        transitions = workflow.get_available_transitions(current_status, user)

        # Filter by conditions
        available = []
        for transition in transitions:
            if self._check_conditions(transition, issue, user):
                available.append(transition)

        return available

    def validate_transition(self, issue, transition, user, data: Dict = None):
        """
        Validate if a transition can be executed.

        Args:
            issue: Issue instance
            transition: Transition instance
            user: User attempting the transition
            data: Optional data for validation

        Returns:
            Dict with validation result
                - valid: Boolean
                - errors: List of error messages

        Raises:
            ValidationError: If transition is invalid
        """
        errors = []
        data = data or {}

        # Check if transition is active
        if not transition.is_active:
            errors.append("Transition is not active")

        # Check if transition is from current status
        if transition.from_status != issue.status:
            errors.append(
                f"Transition cannot be executed from status '{issue.status.name}'"
            )

        # Check conditions
        if not self._check_conditions(transition, issue, user):
            errors.append("Transition conditions not met")

        # Run validators
        validator_errors = self._run_validators(transition, issue, user, data)
        if validator_errors:
            errors.extend(validator_errors)

        # Check user permissions
        if not self._check_transition_permission(transition, issue, user):
            errors.append("User does not have permission to execute this transition")

        if errors:
            raise ValidationError(errors)

        return {
            'valid': True,
            'errors': []
        }

    @transaction.atomic
    def execute_transition(self, issue, transition, user, data: Dict = None, comment: str = None):
        """
        Execute a workflow transition.

        Args:
            issue: Issue instance
            transition: Transition instance
            user: User executing the transition
            data: Optional data for post-functions
            comment: Optional comment to add

        Returns:
            Updated Issue instance

        Raises:
            ValidationError: If transition validation fails
            PermissionDenied: If user lacks permission
        """
        data = data or {}

        # Validate transition
        self.validate_transition(issue, transition, user, data)

        # Store old status for audit
        old_status = issue.status

        # Update issue status
        issue.status = transition.to_status
        issue.updated_by = user
        issue.save(update_fields=['status', 'updated_by', 'updated_at'])

        # Execute post-functions
        self._execute_post_functions(transition, issue, user, data)

        # Add comment if provided
        if comment:
            self._add_transition_comment(issue, user, old_status, transition.to_status, comment)

        # Create audit log
        self._create_audit_log(issue, user, old_status, transition.to_status, transition)

        # TODO: Trigger automation events (Phase 8)
        # TODO: Send notifications (Phase 10)

        return issue

    def _get_workflow_for_issue(self, issue):
        """
        Get the workflow for an issue based on project scheme.

        Args:
            issue: Issue instance

        Returns:
            Workflow instance or None
        """
        try:
            scheme = WorkflowScheme.objects.select_related('default_workflow').get(
                project=issue.project,
                is_active=True
            )
            return scheme.get_workflow_for_issue_type(issue.issue_type)
        except WorkflowScheme.DoesNotExist:
            # No scheme defined for project
            return None

    def _check_conditions(self, transition, issue, user) -> bool:
        """
        Check if transition conditions are met.

        Args:
            transition: Transition instance
            issue: Issue instance
            user: User instance

        Returns:
            Boolean
        """
        if not transition.conditions:
            return True

        conditions = transition.conditions

        # Check user-based conditions
        if 'user_in_role' in conditions:
            required_role = conditions['user_in_role']
            if not self._user_has_role(user, issue.project, required_role):
                return False

        if 'user_is_assignee' in conditions:
            if conditions['user_is_assignee'] and issue.assignee != user:
                return False

        if 'user_is_reporter' in conditions:
            if conditions['user_is_reporter'] and issue.reporter != user:
                return False

        # Check field-based conditions
        if 'field_equals' in conditions:
            for field_name, expected_value in conditions['field_equals'].items():
                actual_value = getattr(issue, field_name, None)
                if actual_value != expected_value:
                    return False

        if 'field_not_empty' in conditions:
            for field_name in conditions['field_not_empty']:
                value = getattr(issue, field_name, None)
                if not value:
                    return False

        # Check issue type condition
        if 'issue_type' in conditions:
            allowed_types = conditions['issue_type']
            if isinstance(allowed_types, list):
                if str(issue.issue_type.id) not in allowed_types:
                    return False

        return True

    def _run_validators(self, transition, issue, user, data: Dict) -> List[str]:
        """
        Run transition validators.

        Args:
            transition: Transition instance
            issue: Issue instance
            user: User instance
            data: Additional data

        Returns:
            List of validation error messages
        """
        errors = []

        if not transition.validators:
            return errors

        validators = transition.validators

        # Field required validators
        if 'field_required' in validators:
            for field_name in validators['field_required']:
                # Check in data first, then on issue
                value = data.get(field_name) or getattr(issue, field_name, None)
                if not value:
                    errors.append(f"Field '{field_name}' is required")

        # Resolution required validator
        if validators.get('resolution_required'):
            if not data.get('resolution') and not getattr(issue, 'resolution', None):
                errors.append("Resolution is required")

        # Comment required validator
        if validators.get('comment_required'):
            if not data.get('comment'):
                errors.append("Comment is required")

        # Custom field validators
        if 'custom_field_required' in validators:
            for field_id in validators['custom_field_required']:
                custom_values = issue.custom_field_values or {}
                if field_id not in custom_values or not custom_values[field_id]:
                    errors.append(f"Custom field '{field_id}' is required")

        return errors

    def _execute_post_functions(self, transition, issue, user, data: Dict):
        """
        Execute post-functions after transition.

        Args:
            transition: Transition instance
            issue: Issue instance
            user: User instance
            data: Additional data
        """
        if not transition.post_functions:
            return

        post_functions = transition.post_functions

        # Assign to user
        if 'assign_to_user' in post_functions:
            user_type = post_functions['assign_to_user']
            if user_type == 'current_user':
                issue.assignee = user
            elif user_type == 'reporter':
                issue.assignee = issue.reporter
            elif user_type == 'project_lead':
                issue.assignee = issue.project.lead
            elif user_type == 'unassigned':
                issue.assignee = None
            issue.save(update_fields=['assignee', 'updated_at'])

        # Update field
        if 'update_field' in post_functions:
            for field_name, value in post_functions['update_field'].items():
                setattr(issue, field_name, value)
            issue.save()

        # Set resolution
        if 'set_resolution' in post_functions:
            resolution = post_functions['set_resolution']
            issue.resolution = resolution
            issue.save(update_fields=['resolution', 'updated_at'])

        # Copy field value
        if 'copy_field' in post_functions:
            for source_field, target_field in post_functions['copy_field'].items():
                value = getattr(issue, source_field, None)
                setattr(issue, target_field, value)
            issue.save()

        # TODO: More post-functions
        # - close_linked_issues
        # - create_linked_issue
        # - send_email
        # - trigger_webhook

    def _check_transition_permission(self, transition, issue, user) -> bool:
        """
        Check if user has permission to execute transition.

        Args:
            transition: Transition instance
            issue: Issue instance
            user: User instance

        Returns:
            Boolean
        """
        # TODO: Implement granular permissions in Phase 4+
        # For now, check if user is project member
        return issue.project.has_member(user)

    def _user_has_role(self, user, project, role_name: str) -> bool:
        """
        Check if user has a specific role in project.

        Args:
            user: User instance
            project: Project instance
            role_name: Role name to check

        Returns:
            Boolean
        """
        from apps.projects.models import ProjectMember

        try:
            membership = ProjectMember.objects.select_related('role').get(
                project=project,
                user=user,
                is_active=True
            )
            return membership.role and membership.role.name == role_name
        except ProjectMember.DoesNotExist:
            return False

    def _add_transition_comment(self, issue, user, old_status, new_status, comment_text):
        """
        Add a comment when transitioning.

        Args:
            issue: Issue instance
            user: User instance
            old_status: Old Status instance
            new_status: New Status instance
            comment_text: Comment text
        """
        # TODO: Implement when Comment model exists (Phase 5)
        pass

    def _create_audit_log(self, issue, user, old_status, new_status, transition):
        """
        Create audit log entry for transition.

        Args:
            issue: Issue instance
            user: User instance
            old_status: Old Status instance
            new_status: New Status instance
            transition: Transition instance
        """
        # TODO: Implement when AuditLog exists (Phase 12)
        pass
