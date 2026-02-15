"""
Signal handlers for automation triggers.

Listens to model signals and triggers automation rules.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from apps.issues.models import Issue, Comment
from apps.automation.services.automation_engine import automation_engine


# Store original values for change detection
_issue_original_values = {}


@receiver(pre_save, sender=Issue)
def store_original_issue_values(sender, instance, **kwargs):
    """
    Store original issue values before save to detect changes.

    Args:
        sender: Model class
        instance: Issue instance
        **kwargs: Additional arguments
    """
    if instance.pk:
        try:
            original = Issue.objects.get(pk=instance.pk)
            _issue_original_values[instance.pk] = {
                'status_id': original.status_id,
                'assignee_id': original.assignee_id,
                'priority_id': original.priority_id,
                'summary': original.summary,
                'description': original.description,
                'custom_field_values': original.custom_field_values.copy() if original.custom_field_values else {},
            }
        except Issue.DoesNotExist:
            pass


@receiver(post_save, sender=Issue)
def trigger_issue_automation(sender, instance, created, **kwargs):
    """
    Trigger automation rules when an issue is created or updated.

    Args:
        sender: Model class
        instance: Issue instance
        created: Boolean indicating if instance was created
        **kwargs: Additional arguments
    """
    # Skip if instance is being deleted
    if instance.deleted_at:
        return

    # Build event data
    event_data = {
        'issue': instance,
        'user': getattr(instance, 'updated_by', None) or getattr(instance, 'created_by', None),
    }

    if created:
        # Issue created event
        event_data['trigger_type'] = 'issue_created'
        event_data['event_type'] = 'issue_created'

        # Trigger automation (async in production)
        automation_engine.process_event(event_data)

    else:
        # Issue updated event
        original = _issue_original_values.get(instance.pk, {})

        # Detect changes
        changed_fields = []
        changes = {}

        if original.get('status_id') != instance.status_id:
            changed_fields.append('status')
            changes['status'] = {
                'old': original.get('status_id'),
                'new': instance.status_id
            }

        if original.get('assignee_id') != instance.assignee_id:
            changed_fields.append('assignee')
            changes['assignee'] = {
                'old': original.get('assignee_id'),
                'new': instance.assignee_id
            }

        if original.get('priority_id') != instance.priority_id:
            changed_fields.append('priority')
            changes['priority'] = {
                'old': original.get('priority_id'),
                'new': instance.priority_id
            }

        if original.get('summary') != instance.summary:
            changed_fields.append('summary')
            changes['summary'] = {
                'old': original.get('summary'),
                'new': instance.summary
            }

        # Check custom field changes
        old_custom_fields = original.get('custom_field_values', {})
        new_custom_fields = instance.custom_field_values or {}

        for field_key in set(list(old_custom_fields.keys()) + list(new_custom_fields.keys())):
            old_value = old_custom_fields.get(field_key)
            new_value = new_custom_fields.get(field_key)

            if old_value != new_value:
                changed_fields.append(field_key)
                changes[field_key] = {
                    'old': old_value,
                    'new': new_value
                }

        if changed_fields:
            event_data['trigger_type'] = 'issue_updated'
            event_data['event_type'] = 'issue_updated'
            event_data['changed_fields'] = changed_fields
            event_data['changes'] = changes

            # Trigger automation (async in production)
            automation_engine.process_event(event_data)

            # Also trigger field_changed events
            for field in changed_fields:
                field_event_data = event_data.copy()
                field_event_data['trigger_type'] = 'field_changed'
                field_event_data['field'] = field

                automation_engine.process_event(field_event_data)

            # Trigger issue_transitioned if status changed
            if 'status' in changed_fields:
                transition_event_data = event_data.copy()
                transition_event_data['trigger_type'] = 'issue_transitioned'

                automation_engine.process_event(transition_event_data)

            # Trigger issue_assigned if assignee changed from None
            if 'assignee' in changed_fields:
                if original.get('assignee_id') is None and instance.assignee_id is not None:
                    assign_event_data = event_data.copy()
                    assign_event_data['trigger_type'] = 'issue_assigned'

                    automation_engine.process_event(assign_event_data)

        # Clean up original values
        if instance.pk in _issue_original_values:
            del _issue_original_values[instance.pk]


@receiver(post_save, sender=Comment)
def trigger_comment_automation(sender, instance, created, **kwargs):
    """
    Trigger automation rules when a comment is added.

    Args:
        sender: Model class
        instance: Comment instance
        created: Boolean indicating if instance was created
        **kwargs: Additional arguments
    """
    if not created:
        return

    # Skip if comment is being deleted
    if instance.deleted_at:
        return

    # Build event data
    event_data = {
        'issue': instance.issue,
        'user': instance.user,
        'trigger_type': 'comment_added',
        'event_type': 'comment_added',
        'comment': instance,
    }

    # Trigger automation (async in production)
    automation_engine.process_event(event_data)
