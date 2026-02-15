"""
Elasticsearch document mappings for search.

Note: Requires django-elasticsearch-dsl to be installed and configured.
"""

from typing import List, Optional

# Placeholder for Elasticsearch documents
# These will be activated once Elasticsearch is properly configured

"""
When Elasticsearch is enabled, uncomment and use:

from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry
from apps.issues.models import Issue


@registry.register_document
class IssueDocument(Document):
    '''
    Elasticsearch document for Issue model.

    Enables full-text search and advanced querying.
    '''

    # Organization and project for filtering
    organization_id = fields.KeywordField()
    organization_name = fields.TextField()
    project_id = fields.KeywordField()
    project_key = fields.KeywordField()
    project_name = fields.TextField()

    # Issue basic fields
    key = fields.KeywordField()
    summary = fields.TextField(
        fields={'raw': fields.KeywordField()}
    )
    description = fields.TextField()

    # Issue type and status
    issue_type_id = fields.KeywordField()
    issue_type_name = fields.TextField(
        fields={'raw': fields.KeywordField()}
    )
    status_id = fields.KeywordField()
    status_name = fields.TextField(
        fields={'raw': fields.KeywordField()}
    )
    status_category = fields.KeywordField()

    # Priority
    priority_id = fields.KeywordField()
    priority_name = fields.TextField(
        fields={'raw': fields.KeywordField()}
    )

    # Users
    reporter_id = fields.KeywordField()
    reporter_email = fields.KeywordField()
    reporter_name = fields.TextField()
    assignee_id = fields.KeywordField()
    assignee_email = fields.KeywordField()
    assignee_name = fields.TextField()

    # Hierarchy
    epic_id = fields.KeywordField()
    epic_key = fields.KeywordField()
    parent_id = fields.KeywordField()
    parent_key = fields.KeywordField()

    # Labels and components
    labels = fields.KeywordField(multi=True)

    # Custom fields (JSONB)
    custom_fields = fields.ObjectField()

    # Dates
    created_at = fields.DateField()
    updated_at = fields.DateField()
    due_date = fields.DateField()
    resolved_at = fields.DateField()

    # Metrics
    story_points = fields.IntegerField()
    time_estimate = fields.IntegerField()
    time_spent = fields.IntegerField()

    # Full-text search field (combines multiple fields)
    full_text = fields.TextField()

    class Index:
        name = 'issues'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 1,
            'max_result_window': 10000,
        }

    class Django:
        model = Issue
        fields = []  # We explicitly define all fields above

        # Fields to exclude from indexing
        ignore_signals = False
        auto_refresh = False

        # Queryset for indexing (only active issues)
        queryset_pagination = 500

    def prepare_organization_id(self, instance):
        return str(instance.project.organization.id)

    def prepare_organization_name(self, instance):
        return instance.project.organization.name

    def prepare_project_id(self, instance):
        return str(instance.project.id)

    def prepare_project_key(self, instance):
        return instance.project.key

    def prepare_project_name(self, instance):
        return instance.project.name

    def prepare_issue_type_id(self, instance):
        return str(instance.issue_type.id) if instance.issue_type else None

    def prepare_issue_type_name(self, instance):
        return instance.issue_type.name if instance.issue_type else None

    def prepare_status_id(self, instance):
        return str(instance.status.id) if instance.status else None

    def prepare_status_name(self, instance):
        return instance.status.name if instance.status else None

    def prepare_status_category(self, instance):
        return instance.status.category if instance.status else None

    def prepare_priority_id(self, instance):
        return str(instance.priority.id) if instance.priority else None

    def prepare_priority_name(self, instance):
        return instance.priority.name if instance.priority else None

    def prepare_reporter_id(self, instance):
        return str(instance.reporter.id) if instance.reporter else None

    def prepare_reporter_email(self, instance):
        return instance.reporter.email if instance.reporter else None

    def prepare_reporter_name(self, instance):
        if instance.reporter:
            return instance.reporter.get_full_name() or instance.reporter.email
        return None

    def prepare_assignee_id(self, instance):
        return str(instance.assignee.id) if instance.assignee else None

    def prepare_assignee_email(self, instance):
        return instance.assignee.email if instance.assignee else None

    def prepare_assignee_name(self, instance):
        if instance.assignee:
            return instance.assignee.get_full_name() or instance.assignee.email
        return None

    def prepare_epic_id(self, instance):
        return str(instance.epic.id) if instance.epic else None

    def prepare_epic_key(self, instance):
        return instance.epic.key if instance.epic else None

    def prepare_parent_id(self, instance):
        return str(instance.parent.id) if instance.parent else None

    def prepare_parent_key(self, instance):
        return instance.parent.key if instance.parent else None

    def prepare_labels(self, instance):
        return list(instance.labels.values_list('name', flat=True))

    def prepare_custom_fields(self, instance):
        return instance.custom_field_values or {}

    def prepare_full_text(self, instance):
        '''Combine multiple fields for full-text search.'''
        parts = [
            instance.key,
            instance.summary,
            instance.description or '',
        ]
        if instance.issue_type:
            parts.append(instance.issue_type.name)
        if instance.status:
            parts.append(instance.status.name)
        if instance.priority:
            parts.append(instance.priority.name)
        if instance.reporter:
            parts.append(instance.reporter.get_full_name() or instance.reporter.email)
        if instance.assignee:
            parts.append(instance.assignee.get_full_name() or instance.assignee.email)

        return ' '.join(filter(None, parts))
"""


class ElasticsearchService:
    """
    Placeholder service for Elasticsearch operations.

    This will be replaced with actual Elasticsearch integration
    when ES is properly configured.
    """

    @staticmethod
    def is_available() -> bool:
        """Check if Elasticsearch is available."""
        return False  # Will be True when ES is configured

    @staticmethod
    def search_issues(query: str, filters: Optional[dict] = None) -> List[dict]:
        """
        Search issues using Elasticsearch.

        Args:
            query: Search query string
            filters: Optional filters dict

        Returns:
            List of matching issue dicts
        """
        # Placeholder - will use actual ES query when configured
        return []

    @staticmethod
    def reindex_all_issues():
        """Rebuild the entire issues index."""
        # Placeholder - will trigger full reindex when ES is configured
        pass

    @staticmethod
    def index_issue(issue_id: str):
        """Index a single issue."""
        # Placeholder - will index single issue when ES is configured
        pass

    @staticmethod
    def delete_issue(issue_id: str):
        """Remove issue from index."""
        # Placeholder - will delete from index when ES is configured
        pass
