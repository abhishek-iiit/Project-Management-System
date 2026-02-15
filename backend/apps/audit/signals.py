"""
Signal handlers for automatic audit logging.
"""

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

# Import will be enabled when models are ready
# from apps.issues.models import Issue, Comment
# from apps.projects.models import Project
# from apps.audit.services import AuditService


# Placeholder signal handlers for automatic audit logging
# These will be activated when the system is fully integrated

"""
@receiver(post_save, sender=Issue)
def audit_issue_save(sender, instance, created, **kwargs):
    '''Audit issue creation and updates.'''
    from apps.audit.utils import ChangeTracker
    
    if created:
        AuditService.log_create(
            entity_type='Issue',
            entity=instance,
            user=getattr(instance, '_audit_user', None),
            organization=instance.project.organization,
            request=getattr(instance, '_audit_request', None),
        )
    else:
        # Get old instance for comparison
        old_instance = getattr(instance, '_audit_old_instance', None)
        if old_instance:
            AuditService.log_update(
                entity_type='Issue',
                entity=instance,
                old_entity=old_instance,
                user=getattr(instance, '_audit_user', None),
                organization=instance.project.organization,
                request=getattr(instance, '_audit_request', None),
            )


@receiver(pre_delete, sender=Issue)
def audit_issue_delete(sender, instance, **kwargs):
    '''Audit issue deletion.'''
    AuditService.log_delete(
        entity_type='Issue',
        entity_id=instance.pk,
        entity_name=instance.key,
        user=getattr(instance, '_audit_user', None),
        organization=instance.project.organization,
        request=getattr(instance, '_audit_request', None),
    )
"""
