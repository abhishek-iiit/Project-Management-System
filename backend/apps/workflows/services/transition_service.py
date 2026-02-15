"""
Transition service for managing workflow transitions.

Following CLAUDE.md best practices:
- Business logic in services
- Transaction management
- DRY principle
"""

from typing import Dict, List
from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied
from apps.common.services import BaseService
from apps.workflows.models import Workflow, Status, Transition


class TransitionService(BaseService):
    """
    Service for managing workflow transitions.

    Handles:
    - Transition CRUD operations
    - Transition validation
    - Bulk transition operations
    """

    @transaction.atomic
    def create_transition(self, workflow: Workflow, data: Dict) -> Transition:
        """
        Create a new transition.

        Args:
            workflow: Workflow instance
            data: Transition data
                - name: str
                - from_status: Status instance or ID
                - to_status: Status instance or ID
                - conditions: dict (optional)
                - validators: dict (optional)
                - post_functions: dict (optional)

        Returns:
            Transition instance

        Raises:
            ValidationError: If validation fails
            PermissionDenied: If user lacks permission
        """
        # Check permission
        if not self._can_manage_workflow(workflow):
            raise PermissionDenied("You don't have permission to manage this workflow")

        # Validate from_status and to_status belong to workflow
        from_status = data.get('from_status')
        to_status = data.get('to_status')

        if from_status and from_status.workflow != workflow:
            raise ValidationError({
                'from_status': 'From status must belong to the workflow'
            })

        if to_status.workflow != workflow:
            raise ValidationError({
                'to_status': 'To status must belong to the workflow'
            })

        # Create transition
        transition = Transition.objects.create(
            workflow=workflow,
            created_by=self.user,
            **data
        )

        return transition

    @transaction.atomic
    def update_transition(self, transition: Transition, data: Dict) -> Transition:
        """
        Update transition details.

        Args:
            transition: Transition instance
            data: Data to update

        Returns:
            Updated Transition instance

        Raises:
            PermissionDenied: If user lacks permission
        """
        # Check permission
        if not self._can_manage_workflow(transition.workflow):
            raise PermissionDenied("You don't have permission to update this transition")

        # Update allowed fields
        allowed_fields = [
            'name', 'description', 'from_status', 'to_status',
            'conditions', 'validators', 'post_functions',
            'is_active', 'position'
        ]

        for field in allowed_fields:
            if field in data:
                setattr(transition, field, data[field])

        transition.updated_by = self.user
        transition.save()

        return transition

    @transaction.atomic
    def delete_transition(self, transition: Transition):
        """
        Soft delete a transition.

        Args:
            transition: Transition instance

        Raises:
            PermissionDenied: If user lacks permission
        """
        # Check permission
        if not self._can_manage_workflow(transition.workflow):
            raise PermissionDenied("You don't have permission to delete this transition")

        # Soft delete
        transition.delete()

    @transaction.atomic
    def bulk_create_transitions(self, workflow: Workflow, transitions_data: List[Dict]) -> List[Transition]:
        """
        Create multiple transitions in a single transaction.

        Args:
            workflow: Workflow instance
            transitions_data: List of transition data dicts

        Returns:
            List of created Transition instances

        Raises:
            ValidationError: If validation fails
            PermissionDenied: If user lacks permission
        """
        # Check permission
        if not self._can_manage_workflow(workflow):
            raise PermissionDenied("You don't have permission to manage this workflow")

        # Create transitions
        transitions = []
        for data in transitions_data:
            transition = Transition(
                workflow=workflow,
                created_by=self.user,
                **data
            )
            transition.full_clean()  # Validate
            transitions.append(transition)

        # Bulk create
        created = Transition.objects.bulk_create(transitions, batch_size=100)

        return created

    def reorder_transitions(self, workflow: Workflow, transition_ids: List[str]):
        """
        Reorder transitions by updating their positions.

        Args:
            workflow: Workflow instance
            transition_ids: List of transition IDs in desired order

        Raises:
            PermissionDenied: If user lacks permission
        """
        # Check permission
        if not self._can_manage_workflow(workflow):
            raise PermissionDenied("You don't have permission to manage this workflow")

        # Update positions
        transitions = []
        for position, transition_id in enumerate(transition_ids):
            try:
                transition = Transition.objects.get(
                    id=transition_id,
                    workflow=workflow
                )
                transition.position = position
                transition.updated_by = self.user
                transitions.append(transition)
            except Transition.DoesNotExist:
                continue

        # Bulk update
        if transitions:
            Transition.objects.bulk_update(
                transitions,
                fields=['position', 'updated_by', 'updated_at'],
                batch_size=100
            )

    def add_condition(self, transition: Transition, condition_type: str, condition_value):
        """
        Add a condition to a transition.

        Args:
            transition: Transition instance
            condition_type: Type of condition (e.g., 'user_in_role')
            condition_value: Value for the condition

        Raises:
            PermissionDenied: If user lacks permission
        """
        # Check permission
        if not self._can_manage_workflow(transition.workflow):
            raise PermissionDenied("You don't have permission to update this transition")

        # Add condition
        if not transition.conditions:
            transition.conditions = {}

        transition.conditions[condition_type] = condition_value
        transition.updated_by = self.user
        transition.save(update_fields=['conditions', 'updated_by', 'updated_at'])

    def remove_condition(self, transition: Transition, condition_type: str):
        """
        Remove a condition from a transition.

        Args:
            transition: Transition instance
            condition_type: Type of condition to remove

        Raises:
            PermissionDenied: If user lacks permission
        """
        # Check permission
        if not self._can_manage_workflow(transition.workflow):
            raise PermissionDenied("You don't have permission to update this transition")

        # Remove condition
        if transition.conditions and condition_type in transition.conditions:
            del transition.conditions[condition_type]
            transition.updated_by = self.user
            transition.save(update_fields=['conditions', 'updated_by', 'updated_at'])

    def add_validator(self, transition: Transition, validator_type: str, validator_value=None):
        """
        Add a validator to a transition.

        Args:
            transition: Transition instance
            validator_type: Type of validator (e.g., 'field_required')
            validator_value: Value for the validator (optional)

        Raises:
            PermissionDenied: If user lacks permission
        """
        # Check permission
        if not self._can_manage_workflow(transition.workflow):
            raise PermissionDenied("You don't have permission to update this transition")

        # Add validator
        if not transition.validators:
            transition.validators = {}

        transition.validators[validator_type] = validator_value if validator_value is not None else True
        transition.updated_by = self.user
        transition.save(update_fields=['validators', 'updated_by', 'updated_at'])

    def add_post_function(self, transition: Transition, function_type: str, function_value):
        """
        Add a post-function to a transition.

        Args:
            transition: Transition instance
            function_type: Type of post-function (e.g., 'assign_to_user')
            function_value: Value for the post-function

        Raises:
            PermissionDenied: If user lacks permission
        """
        # Check permission
        if not self._can_manage_workflow(transition.workflow):
            raise PermissionDenied("You don't have permission to update this transition")

        # Add post-function
        if not transition.post_functions:
            transition.post_functions = {}

        transition.post_functions[function_type] = function_value
        transition.updated_by = self.user
        transition.save(update_fields=['post_functions', 'updated_by', 'updated_at'])

    # Permission helpers

    def _can_manage_workflow(self, workflow: Workflow) -> bool:
        """Check if user can manage workflow."""
        from apps.organizations.models import OrganizationMember

        try:
            membership = OrganizationMember.objects.get(
                organization=workflow.organization,
                user=self.user,
                is_active=True
            )
            # Check if user can manage workflows (admin or owner)
            return membership.role in ['owner', 'admin']
        except OrganizationMember.DoesNotExist:
            return False
