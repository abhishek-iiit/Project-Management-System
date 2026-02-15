"""
Signal handlers for automatic notification creation.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

# Import will be enabled when issue models are ready
# from apps.issues.models import Issue, Comment
# from apps.boards.models import Sprint
# from apps.notifications.services import NotificationService


# Placeholder signal handlers
# These will be activated when the system is fully integrated

"""
@receiver(post_save, sender=Issue)
def notify_on_issue_created(sender, instance, created, **kwargs):
    '''Notify users when an issue is created.'''
    if created:
        service = NotificationService(organization=instance.project.organization)
        service.notify_issue_created(
            issue=instance,
            actor=instance.reporter,
            watchers=list(instance.watchers.all()),
        )


@receiver(post_save, sender=Comment)
def notify_on_comment_added(sender, instance, created, **kwargs):
    '''Notify users when a comment is added.'''
    if created:
        service = NotificationService(organization=instance.issue.project.organization)
        service.notify_issue_commented(
            issue=instance.issue,
            comment=instance,
            actor=instance.created_by,
        )
"""
