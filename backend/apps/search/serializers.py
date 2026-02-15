"""
Serializers for search and saved filters.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model

from apps.search.models import SavedFilter, SearchHistory
from apps.search.services.jql_parser import JQLService

User = get_user_model()


class SavedFilterSerializer(serializers.ModelSerializer):
    """Serializer for SavedFilter model."""

    # Read-only fields
    organization_name = serializers.CharField(
        source='organization.name',
        read_only=True
    )
    project_key = serializers.CharField(
        source='project.key',
        read_only=True,
        allow_null=True
    )
    project_name = serializers.CharField(
        source='project.name',
        read_only=True,
        allow_null=True
    )
    created_by_email = serializers.EmailField(
        source='created_by.email',
        read_only=True,
        allow_null=True
    )
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = SavedFilter
        fields = [
            'id',
            'organization',
            'organization_name',
            'project',
            'project_key',
            'project_name',
            'name',
            'description',
            'jql',
            'is_shared',
            'is_favorite',
            'usage_count',
            'last_used_at',
            'config',
            'created_by',
            'created_by_email',
            'created_by_name',
            'updated_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'usage_count',
            'last_used_at',
            'created_by',
            'updated_by',
            'created_at',
            'updated_at',
        ]

    def get_created_by_name(self, obj):
        """Get creator's display name."""
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.email
        return None

    def validate_jql(self, value):
        """Validate JQL syntax."""
        is_valid, error = JQLService.validate_jql(value)
        if not is_valid:
            raise serializers.ValidationError(f"Invalid JQL: {error}")
        return value

    def validate(self, attrs):
        """Validate the entire filter."""
        # Ensure project belongs to organization if provided
        if 'project' in attrs and attrs['project']:
            if attrs['project'].organization != attrs['organization']:
                raise serializers.ValidationError({
                    'project': 'Project must belong to the specified organization'
                })
        return attrs


class SavedFilterCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a saved filter."""

    class Meta:
        model = SavedFilter
        fields = [
            'organization',
            'project',
            'name',
            'description',
            'jql',
            'is_shared',
            'is_favorite',
            'config',
        ]

    def validate_jql(self, value):
        """Validate JQL syntax."""
        is_valid, error = JQLService.validate_jql(value)
        if not is_valid:
            raise serializers.ValidationError(f"Invalid JQL: {error}")
        return value


class SavedFilterUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a saved filter."""

    class Meta:
        model = SavedFilter
        fields = [
            'name',
            'description',
            'jql',
            'is_shared',
            'is_favorite',
            'config',
        ]

    def validate_jql(self, value):
        """Validate JQL syntax."""
        if value:
            is_valid, error = JQLService.validate_jql(value)
            if not is_valid:
                raise serializers.ValidationError(f"Invalid JQL: {error}")
        return value


class SavedFilterListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing saved filters."""

    project_key = serializers.CharField(
        source='project.key',
        read_only=True,
        allow_null=True
    )
    created_by_email = serializers.EmailField(
        source='created_by.email',
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = SavedFilter
        fields = [
            'id',
            'name',
            'description',
            'jql',
            'project_key',
            'is_shared',
            'is_favorite',
            'usage_count',
            'last_used_at',
            'created_by_email',
            'created_at',
        ]


class SavedFilterCloneSerializer(serializers.Serializer):
    """Serializer for cloning a saved filter."""

    name = serializers.CharField(
        max_length=200,
        required=False,
        help_text="Name for the cloned filter"
    )


class SearchHistorySerializer(serializers.ModelSerializer):
    """Serializer for SearchHistory model."""

    user_email = serializers.EmailField(
        source='user.email',
        read_only=True
    )

    class Meta:
        model = SearchHistory
        fields = [
            'id',
            'organization',
            'user',
            'user_email',
            'query',
            'query_type',
            'results_count',
            'execution_time_ms',
            'created_at',
        ]
        read_only_fields = fields


class JQLValidationSerializer(serializers.Serializer):
    """Serializer for JQL validation request."""

    jql = serializers.CharField(
        required=True,
        help_text="JQL query to validate"
    )


class JQLValidationResponseSerializer(serializers.Serializer):
    """Serializer for JQL validation response."""

    is_valid = serializers.BooleanField()
    error_message = serializers.CharField(
        allow_null=True,
        required=False
    )


class SearchRequestSerializer(serializers.Serializer):
    """Serializer for search request."""

    jql = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="JQL query string"
    )
    project = serializers.UUIDField(
        required=False,
        help_text="Filter by project ID"
    )
    issue_type = serializers.UUIDField(
        required=False,
        help_text="Filter by issue type ID"
    )
    status = serializers.UUIDField(
        required=False,
        help_text="Filter by status ID"
    )
    priority = serializers.UUIDField(
        required=False,
        help_text="Filter by priority ID"
    )
    assignee = serializers.CharField(
        required=False,
        help_text="Filter by assignee (user ID, 'currentUser', or 'unassigned')"
    )
    reporter = serializers.CharField(
        required=False,
        help_text="Filter by reporter (user ID or 'currentUser')"
    )
    labels = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Filter by labels"
    )
    text = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Full-text search"
    )
    created_after = serializers.DateTimeField(
        required=False,
        help_text="Created after this date"
    )
    created_before = serializers.DateTimeField(
        required=False,
        help_text="Created before this date"
    )
    updated_after = serializers.DateTimeField(
        required=False,
        help_text="Updated after this date"
    )
    updated_before = serializers.DateTimeField(
        required=False,
        help_text="Updated before this date"
    )
    use_elasticsearch = serializers.BooleanField(
        default=False,
        required=False,
        help_text="Use Elasticsearch for search (if available)"
    )


class AutocompleteRequestSerializer(serializers.Serializer):
    """Serializer for autocomplete request."""

    field = serializers.ChoiceField(
        choices=[
            'assignee',
            'reporter',
            'labels',
            'project',
            'status',
            'priority',
        ],
        required=True,
        help_text="Field to get suggestions for"
    )
    query = serializers.CharField(
        required=True,
        allow_blank=True,
        help_text="Partial query string"
    )
    limit = serializers.IntegerField(
        default=10,
        min_value=1,
        max_value=50,
        required=False,
        help_text="Maximum number of suggestions"
    )


class AutocompleteResponseSerializer(serializers.Serializer):
    """Serializer for autocomplete response."""

    suggestions = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of suggestions"
    )


class SearchStatsSerializer(serializers.Serializer):
    """Serializer for search statistics."""

    total_searches = serializers.IntegerField()
    avg_execution_time_ms = serializers.FloatField()
    popular_queries = serializers.ListField(
        child=serializers.DictField()
    )
    recent_searches = SearchHistorySerializer(many=True)
