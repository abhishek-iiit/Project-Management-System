"""
Signal handlers for search indexing.

Automatically index/update/delete issues in Elasticsearch when they change.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

# Import will be enabled when Elasticsearch is configured
# from apps.issues.models import Issue
# from apps.search.documents import ElasticsearchService


# Placeholder signal handlers for Elasticsearch indexing
# These will be activated when Elasticsearch is properly configured

"""
@receiver(post_save, sender=Issue)
def index_issue_on_save(sender, instance, created, **kwargs):
    '''Index or update issue in Elasticsearch when saved.'''
    try:
        ElasticsearchService.index_issue(str(instance.id))
    except Exception as e:
        # Log error but don't fail the save operation
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to index issue {instance.key}: {str(e)}")


@receiver(post_delete, sender=Issue)
def remove_issue_from_index(sender, instance, **kwargs):
    '''Remove issue from Elasticsearch when deleted.'''
    try:
        ElasticsearchService.delete_issue(str(instance.id))
    except Exception as e:
        # Log error but don't fail the delete operation
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to remove issue {instance.key} from index: {str(e)}")
"""
