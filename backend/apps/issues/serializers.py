"""
Issue serializers for API endpoints.

Following CLAUDE.md best practices:
- Efficient data transformation
- Nested relationships with prefetch optimization
- Validation at serializer level
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.issues.models import (
    Issue, IssueType, Priority, Label, Comment, Attachment,
    IssueLink, IssueLinkType, Watcher
)
from apps.projects.models import Project
from apps.workflows.models import Status
from apps.workflows.serializers import StatusMinimalSerializer

User = get_user_model()


class IssueTypeSerializer(serializers.ModelSerializer):
    """Serializer for issue type model."""

    organization_name = serializers.CharField(source='organization.name', read_only=True)

    class Meta:
        model = IssueType
        fields = [
            'id', 'name', 'description', 'icon', 'color',
            'is_subtask', 'is_epic', 'is_default', 'is_active',
            'position', 'organization', 'organization_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PrioritySerializer(serializers.ModelSerializer):
    """Serializer for priority model."""

    organization_name = serializers.CharField(source='organization.name', read_only=True)

    class Meta:
        model = Priority
        fields = [
            'id', 'name', 'description', 'icon', 'color',
            'level', 'is_default', 'is_active',
            'organization', 'organization_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class LabelSerializer(serializers.ModelSerializer):
    """Serializer for label model."""

    class Meta:
        model = Label
        fields = ['id', 'name', 'color', 'project', 'organization']
        read_only_fields = ['id']


class WatcherSerializer(serializers.ModelSerializer):
    """Serializer for watcher model."""

    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = Watcher
        fields = ['id', 'user', 'user_email', 'user_name', 'created_at']
        read_only_fields = ['id', 'created_at']


class CommentSerializer(serializers.ModelSerializer):
    """Serializer for comment model."""

    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    mentions_count = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id', 'issue', 'user', 'user_email', 'user_name',
            'body', 'mentions_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def get_mentions_count(self, obj):
        """Get count of mentions."""
        return obj.mentions.count()


class AttachmentSerializer(serializers.ModelSerializer):
    """Serializer for attachment model."""

    uploaded_by = serializers.CharField(source='created_by.full_name', read_only=True)
    file_url = serializers.SerializerMethodField()
    is_image = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = [
            'id', 'issue', 'file', 'file_url', 'filename',
            'file_size', 'mime_type', 'is_image',
            'uploaded_by', 'created_at'
        ]
        read_only_fields = ['id', 'filename', 'file_size', 'mime_type', 'created_at']

    def get_file_url(self, obj):
        """Get file URL."""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None

    def get_is_image(self, obj):
        """Check if attachment is an image."""
        return obj.is_image()


class IssueLinkTypeSerializer(serializers.ModelSerializer):
    """Serializer for issue link type model."""

    organization_name = serializers.CharField(source='organization.name', read_only=True)

    class Meta:
        model = IssueLinkType
        fields = [
            'id', 'name', 'inward_description', 'outward_description',
            'is_active', 'organization', 'organization_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class IssueLinkSerializer(serializers.ModelSerializer):
    """Serializer for issue link model."""

    from_issue_key = serializers.CharField(source='from_issue.key', read_only=True)
    from_issue_summary = serializers.CharField(source='from_issue.summary', read_only=True)
    to_issue_key = serializers.CharField(source='to_issue.key', read_only=True)
    to_issue_summary = serializers.CharField(source='to_issue.summary', read_only=True)
    link_type_name = serializers.CharField(source='link_type.name', read_only=True)
    outward_description = serializers.CharField(source='link_type.outward_description', read_only=True)
    inward_description = serializers.CharField(source='link_type.inward_description', read_only=True)

    class Meta:
        model = IssueLink
        fields = [
            'id', 'from_issue', 'from_issue_key', 'from_issue_summary',
            'to_issue', 'to_issue_key', 'to_issue_summary',
            'link_type', 'link_type_name',
            'outward_description', 'inward_description',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def validate(self, data):
        """Cross-field validation."""
        from_issue = data.get('from_issue')
        to_issue = data.get('to_issue')

        if from_issue == to_issue:
            raise serializers.ValidationError({
                'to_issue': 'Cannot link issue to itself'
            })

        if from_issue.project.organization != to_issue.project.organization:
            raise serializers.ValidationError({
                'to_issue': 'Can only link issues within the same organization'
            })

        return data


class IssueMinimalSerializer(serializers.ModelSerializer):
    """Minimal issue serializer for nested relationships."""

    project_key = serializers.CharField(source='project.key', read_only=True)
    issue_type_name = serializers.CharField(source='issue_type.name', read_only=True)
    status_name = serializers.CharField(source='status.name', read_only=True)
    status_category = serializers.CharField(source='status.category', read_only=True)
    priority_name = serializers.CharField(source='priority.name', read_only=True, allow_null=True)
    assignee_name = serializers.CharField(source='assignee.full_name', read_only=True, allow_null=True)

    class Meta:
        model = Issue
        fields = [
            'id', 'key', 'summary',
            'project', 'project_key',
            'issue_type', 'issue_type_name',
            'status', 'status_name', 'status_category',
            'priority', 'priority_name',
            'assignee', 'assignee_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'key', 'created_at', 'updated_at']


class IssueSerializer(serializers.ModelSerializer):
    """Full issue serializer with all details."""

    # Project details
    project_key = serializers.CharField(source='project.key', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)

    # Issue type details
    issue_type_name = serializers.CharField(source='issue_type.name', read_only=True)
    issue_type_icon = serializers.CharField(source='issue_type.icon', read_only=True)

    # Status details
    status_name = serializers.CharField(source='status.name', read_only=True)
    status_category = serializers.CharField(source='status.category', read_only=True)

    # Priority details
    priority_name = serializers.CharField(source='priority.name', read_only=True, allow_null=True)

    # User details
    reporter_name = serializers.CharField(source='reporter.full_name', read_only=True)
    reporter_email = serializers.EmailField(source='reporter.email', read_only=True)
    assignee_name = serializers.CharField(source='assignee.full_name', read_only=True, allow_null=True)
    assignee_email = serializers.EmailField(source='assignee.email', read_only=True, allow_null=True)

    # Hierarchy
    epic_key = serializers.CharField(source='epic.key', read_only=True, allow_null=True)
    epic_summary = serializers.CharField(source='epic.summary', read_only=True, allow_null=True)
    parent_key = serializers.CharField(source='parent.key', read_only=True, allow_null=True)
    parent_summary = serializers.CharField(source='parent.summary', read_only=True, allow_null=True)

    # Nested relationships
    labels = LabelSerializer(many=True, read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)
    watchers = WatcherSerializer(many=True, read_only=True)

    # Counts
    comments_count = serializers.SerializerMethodField()
    attachments_count = serializers.SerializerMethodField()
    watchers_count = serializers.SerializerMethodField()
    subtasks_count = serializers.SerializerMethodField()
    links_count = serializers.SerializerMethodField()

    # Computed fields
    is_subtask = serializers.SerializerMethodField()
    is_epic = serializers.SerializerMethodField()

    class Meta:
        model = Issue
        fields = [
            'id', 'key', 'summary', 'description',
            'project', 'project_key', 'project_name',
            'issue_type', 'issue_type_name', 'issue_type_icon',
            'status', 'status_name', 'status_category',
            'priority', 'priority_name',
            'reporter', 'reporter_name', 'reporter_email',
            'assignee', 'assignee_name', 'assignee_email',
            'epic', 'epic_key', 'epic_summary',
            'parent', 'parent_key', 'parent_summary',
            'original_estimate', 'remaining_estimate', 'time_spent',
            'due_date', 'resolution_date', 'resolution',
            'custom_field_values',
            'labels', 'comments', 'attachments', 'watchers',
            'comments_count', 'attachments_count', 'watchers_count',
            'subtasks_count', 'links_count',
            'is_subtask', 'is_epic',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'key', 'reporter', 'created_at', 'updated_at',
            'comments_count', 'attachments_count', 'watchers_count',
            'subtasks_count', 'links_count'
        ]

    def get_comments_count(self, obj):
        """Get comments count."""
        return obj.comments.count()

    def get_attachments_count(self, obj):
        """Get attachments count."""
        return obj.attachments.count()

    def get_watchers_count(self, obj):
        """Get watchers count."""
        return obj.watchers.count()

    def get_subtasks_count(self, obj):
        """Get subtasks count."""
        return obj.subtasks.count()

    def get_links_count(self, obj):
        """Get links count."""
        return obj.outward_links.count() + obj.inward_links.count()

    def get_is_subtask(self, obj):
        """Check if issue is a subtask."""
        return obj.is_subtask()

    def get_is_epic(self, obj):
        """Check if issue is an epic."""
        return obj.is_epic()


class IssueCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating issues."""

    project = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(),
        required=True
    )

    issue_type = serializers.PrimaryKeyRelatedField(
        queryset=IssueType.objects.all(),
        required=True
    )

    priority = serializers.PrimaryKeyRelatedField(
        queryset=Priority.objects.all(),
        required=False,
        allow_null=True
    )

    assignee = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True
    )

    epic = serializers.PrimaryKeyRelatedField(
        queryset=Issue.objects.all(),
        required=False,
        allow_null=True
    )

    parent = serializers.PrimaryKeyRelatedField(
        queryset=Issue.objects.all(),
        required=False,
        allow_null=True
    )

    labels = serializers.PrimaryKeyRelatedField(
        queryset=Label.objects.all(),
        many=True,
        required=False
    )

    class Meta:
        model = Issue
        fields = [
            'summary', 'description',
            'project', 'issue_type', 'priority',
            'assignee', 'epic', 'parent',
            'original_estimate', 'due_date',
            'custom_field_values', 'labels'
        ]

    def validate_project(self, value):
        """Validate user has access to project."""
        user = self.context['request'].user

        if not value.has_member(user):
            raise serializers.ValidationError(
                "You are not a member of this project"
            )

        return value

    def validate_epic(self, value):
        """Validate epic belongs to same project."""
        if value and self.initial_data.get('project'):
            project = Project.objects.get(id=self.initial_data['project'])
            if value.project != project:
                raise serializers.ValidationError(
                    "Epic must belong to the same project"
                )

            if not value.is_epic():
                raise serializers.ValidationError(
                    "Referenced issue is not an epic"
                )

        return value

    def validate_parent(self, value):
        """Validate parent belongs to same project."""
        if value and self.initial_data.get('project'):
            project = Project.objects.get(id=self.initial_data['project'])
            if value.project != project:
                raise serializers.ValidationError(
                    "Parent must belong to the same project"
                )

        return value


class IssueUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating issues."""

    labels = serializers.PrimaryKeyRelatedField(
        queryset=Label.objects.all(),
        many=True,
        required=False
    )

    class Meta:
        model = Issue
        fields = [
            'summary', 'description',
            'issue_type', 'priority', 'assignee',
            'epic', 'parent',
            'original_estimate', 'remaining_estimate',
            'due_date', 'resolution',
            'custom_field_values', 'labels'
        ]


class TransitionIssueSerializer(serializers.Serializer):
    """Serializer for transitioning issues."""

    transition_id = serializers.UUIDField(required=True)
    comment = serializers.CharField(required=False, allow_blank=True)
    resolution = serializers.CharField(required=False, allow_blank=True)

    # Additional data for validators/post-functions
    additional_data = serializers.JSONField(required=False)


class AddLinkSerializer(serializers.Serializer):
    """Serializer for adding issue links."""

    to_issue_id = serializers.UUIDField(required=True)
    link_type_id = serializers.UUIDField(required=True)

    def validate_to_issue_id(self, value):
        """Validate target issue exists."""
        try:
            Issue.objects.get(id=value)
        except Issue.DoesNotExist:
            raise serializers.ValidationError("Target issue does not exist")
        return value

    def validate_link_type_id(self, value):
        """Validate link type exists."""
        try:
            IssueLinkType.objects.get(id=value)
        except IssueLinkType.DoesNotExist:
            raise serializers.ValidationError("Link type does not exist")
        return value


class AddWatcherSerializer(serializers.Serializer):
    """Serializer for adding watchers."""

    user_id = serializers.UUIDField(required=True)

    def validate_user_id(self, value):
        """Validate user exists."""
        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist")
        return value


class LogWorkSerializer(serializers.Serializer):
    """Serializer for logging work."""

    time_spent = serializers.IntegerField(required=True, min_value=1)
    comment = serializers.CharField(required=False, allow_blank=True)

    def validate_time_spent(self, value):
        """Validate time spent is positive."""
        if value <= 0:
            raise serializers.ValidationError("Time spent must be positive")
        return value
