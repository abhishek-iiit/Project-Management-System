"""
Automation engine - orchestrates rule execution.

Following CLAUDE.md best practices:
- Service layer for complex operations
- Transaction management
"""

from typing import Dict, Any, List
import time
from django.db import transaction
from django.contrib.auth import get_user_model

from apps.automation.models import AutomationRule, AutomationExecution, ExecutionStatus
from apps.automation.triggers.issue_triggers import get_trigger
from apps.automation.conditions.field_conditions import get_condition
from apps.automation.actions.issue_actions import get_action

User = get_user_model()


class AutomationEngine:
    """
    Automation engine for executing automation rules.

    Evaluates triggers, conditions, and executes actions.
    """

    def __init__(self):
        """Initialize automation engine."""
        pass

    def process_event(self, event_data: Dict[str, Any]) -> List[AutomationExecution]:
        """
        Process an event and execute matching automation rules.

        Args:
            event_data: Event data including issue, user, trigger type, etc.

        Returns:
            List of AutomationExecution instances
        """
        executions = []

        # Get issue and organization from event
        issue = event_data.get('issue')
        if not issue:
            return executions

        organization = issue.project.organization

        # Get trigger type
        trigger_type = event_data.get('trigger_type')
        if not trigger_type:
            return executions

        # Find matching rules
        rules = AutomationRule.objects.filter(
            organization=organization,
            trigger_type=trigger_type,
            is_active=True
        ).for_project(issue.project)

        # Execute each matching rule
        for rule in rules:
            execution = self.execute_rule(rule, event_data)
            if execution:
                executions.append(execution)

        return executions

    @transaction.atomic
    def execute_rule(
        self,
        rule: AutomationRule,
        event_data: Dict[str, Any]
    ) -> AutomationExecution:
        """
        Execute a single automation rule.

        Args:
            rule: AutomationRule instance
            event_data: Event data

        Returns:
            AutomationExecution instance
        """
        start_time = time.time()

        # Create execution record
        execution = AutomationExecution.objects.create(
            rule=rule,
            issue=event_data.get('issue'),
            trigger_event=event_data,
            status=ExecutionStatus.FAILED  # Will update later
        )

        try:
            # Check if rule should execute for this event
            if not rule.should_execute_for_event(event_data):
                execution_time_ms = int((time.time() - start_time) * 1000)
                execution.mark_failed(
                    'Rule did not match event',
                    execution_time_ms=execution_time_ms
                )
                return execution

            # Evaluate conditions
            conditions_passed, conditions_result = self.evaluate_conditions(
                rule,
                event_data
            )

            if not conditions_passed:
                execution_time_ms = int((time.time() - start_time) * 1000)
                execution.conditions_result = conditions_result
                execution.mark_failed(
                    'Conditions not met',
                    error_details=conditions_result,
                    execution_time_ms=execution_time_ms
                )
                return execution

            # Execute actions
            actions_result, all_actions_succeeded = self.execute_actions(
                rule,
                event_data
            )

            execution_time_ms = int((time.time() - start_time) * 1000)

            if all_actions_succeeded:
                execution.mark_success(
                    conditions_result,
                    actions_result,
                    execution_time_ms
                )
            else:
                execution.mark_partial(
                    conditions_result,
                    actions_result,
                    'Some actions failed',
                    execution_time_ms
                )

            # Update rule execution count
            rule.increment_execution_count()

            return execution

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            execution.mark_failed(
                str(e),
                error_details={'exception': str(type(e).__name__)},
                execution_time_ms=execution_time_ms
            )
            return execution

    def evaluate_conditions(
        self,
        rule: AutomationRule,
        event_data: Dict[str, Any]
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Evaluate all conditions for a rule.

        Args:
            rule: AutomationRule instance
            event_data: Event data

        Returns:
            Tuple of (all_passed, results_dict)
        """
        # Build execution context
        context = {
            'issue': event_data.get('issue'),
            'user': event_data.get('user'),
            'event': event_data,
            'changes': event_data.get('changes', {}),
        }

        results = {}
        all_passed = True

        # If no conditions, they all pass
        if not rule.conditions:
            return True, {}

        # Evaluate each condition
        for idx, condition_def in enumerate(rule.conditions):
            condition_type = condition_def.get('type')
            condition_config = condition_def.get('config', {})

            try:
                # Get condition instance
                condition = get_condition(condition_type, condition_config)

                # Evaluate condition
                passed = condition.evaluate(context)

                results[f'condition_{idx}'] = {
                    'type': condition_type,
                    'passed': passed,
                    'config': condition_config
                }

                if not passed:
                    all_passed = False

            except Exception as e:
                results[f'condition_{idx}'] = {
                    'type': condition_type,
                    'passed': False,
                    'error': str(e)
                }
                all_passed = False

        return all_passed, results

    def execute_actions(
        self,
        rule: AutomationRule,
        event_data: Dict[str, Any]
    ) -> tuple[Dict[str, Any], bool]:
        """
        Execute all actions for a rule.

        Args:
            rule: AutomationRule instance
            event_data: Event data

        Returns:
            Tuple of (results_dict, all_succeeded)
        """
        # Build execution context
        context = {
            'issue': event_data.get('issue'),
            'user': event_data.get('user'),
            'event': event_data,
            'changes': event_data.get('changes', {}),
        }

        results = {}
        all_succeeded = True

        # Execute each action
        for idx, action_def in enumerate(rule.actions):
            action_type = action_def.get('type')
            action_config = action_def.get('config', {})

            try:
                # Get action instance
                action = get_action(action_type, action_config)

                # Execute action
                action_result = action.execute(context)

                results[f'action_{idx}'] = {
                    'type': action_type,
                    'result': action_result,
                    'config': action_config
                }

                if not action_result.get('success', False):
                    all_succeeded = False

            except Exception as e:
                results[f'action_{idx}'] = {
                    'type': action_type,
                    'error': str(e),
                    'success': False
                }
                all_succeeded = False

        return results, all_succeeded


# Global engine instance
automation_engine = AutomationEngine()
