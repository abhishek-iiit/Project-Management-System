"""
Board serializers.

Following CLAUDE.md best practices:
- Comprehensive validation
- Nested relationships
- Read-only computed fields
"""

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from apps.boards.models import Board, BoardIssue, Sprint, BoardType, SprintState
from apps.issues.serializers import IssueSerializer


class BoardSerializer(serializers.ModelSerializer):
    """Serializer for boards."""

    # Read-only fields
    project_key = serializers.CharField(source='project.key', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    board_type_display = serializers.CharField(
        source='get_board_type_display',
        read_only=True
    )

    # Computed fields
    active_sprint = serializers.SerializerMethodField()
    total_issues = serializers.SerializerMethodField()

    class Meta:
        model = Board
        fields = [
            'id',
            'project',
            'project_key',
            'project_name',
            'name',
            'description',
            'board_type',
            'board_type_display',
            'column_config',
            'swimlane_config',
            'quick_filters',
            'filter_query',
            'estimation_field',
            'is_active',
            'active_sprint',
            'total_issues',
            'created_by',
            'updated_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'project_key',
            'project_name',
            'board_type_display',
            'active_sprint',
            'total_issues',
            'created_by',
            'updated_by',
            'created_at',
            'updated_at',
        ]

    def get_active_sprint(self, obj):
        """Get active sprint for Scrum boards."""
        if obj.board_type != BoardType.SCRUM:
            return None

        sprint = obj.get_active_sprint()
        if not sprint:
            return None

        return {
            'id': str(sprint.id),
            'name': sprint.name,
            'start_date': sprint.start_date,
            'end_date': sprint.end_date,
        }

    def get_total_issues(self, obj):
        """Get total issues on board."""
        return obj.board_issues.count()

    def validate_column_config(self, value):
        """Validate column configuration."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Column config must be a dictionary")

        columns = value.get('columns', [])
        if not isinstance(columns, list):
            raise serializers.ValidationError("columns must be a list")

        for idx, column in enumerate(columns):
            if not isinstance(column, dict):
                raise serializers.ValidationError(f"Column {idx} must be a dictionary")
            if 'name' not in column or 'status_ids' not in column:
                raise serializers.ValidationError(
                    f"Column {idx} must have 'name' and 'status_ids'"
                )

        return value

    def validate_swimlane_config(self, value):
        """Validate swimlane configuration."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Swimlane config must be a dictionary")

        swimlane_type = value.get('type')
        if swimlane_type and swimlane_type not in ['assignee', 'priority', 'epic', 'issue_type', 'none']:
            raise serializers.ValidationError(f"Invalid swimlane type: {swimlane_type}")

        return value


class BoardCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating boards."""

    class Meta:
        model = Board
        fields = [
            'project',
            'name',
            'description',
            'board_type',
            'column_config',
            'swimlane_config',
            'quick_filters',
            'filter_query',
            'estimation_field',
            'is_active',
        ]


class BoardIssueSerializer(serializers.ModelSerializer):
    """Serializer for board issues."""

    # Issue details
    issue = IssueSerializer(read_only=True)
    issue_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = BoardIssue
        fields = [
            'id',
            'board',
            'issue',
            'issue_id',
            'rank',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
        ]


class SprintSerializer(serializers.ModelSerializer):
    """Serializer for sprints."""

    # Read-only fields
    board_name = serializers.CharField(source='board.name', read_only=True)
    state_display = serializers.CharField(source='get_state_display', read_only=True)

    # Computed fields
    total_issues = serializers.SerializerMethodField()
    completed_issues = serializers.SerializerMethodField()
    total_points = serializers.SerializerMethodField()
    completed_points = serializers.SerializerMethodField()
    progress_percentage = serializers.SerializerMethodField()
    days_remaining = serializers.SerializerMethodField()

    class Meta:
        model = Sprint
        fields = [
            'id',
            'board',
            'board_name',
            'name',
            'goal',
            'start_date',
            'end_date',
            'completed_date',
            'state',
            'state_display',
            'total_issues',
            'completed_issues',
            'total_points',
            'completed_points',
            'progress_percentage',
            'days_remaining',
            'created_by',
            'updated_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'board_name',
            'state_display',
            'completed_date',
            'total_issues',
            'completed_issues',
            'total_points',
            'completed_points',
            'progress_percentage',
            'days_remaining',
            'created_by',
            'updated_by',
            'created_at',
            'updated_at',
        ]

    def get_total_issues(self, obj):
        """Get total issues in sprint."""
        return obj.issues.count()

    def get_completed_issues(self, obj):
        """Get completed issues count."""
        return obj.get_completed_issues().count()

    def get_total_points(self, obj):
        """Get total story points."""
        return float(obj.calculate_total_points())

    def get_completed_points(self, obj):
        """Get completed story points."""
        return float(obj.calculate_completed_points())

    def get_progress_percentage(self, obj):
        """Get progress percentage."""
        return obj.get_progress_percentage()

    def get_days_remaining(self, obj):
        """Get days remaining."""
        return obj.get_days_remaining()

    def validate(self, attrs):
        """Cross-field validation."""
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')

        if start_date and end_date:
            if start_date >= end_date:
                raise serializers.ValidationError({
                    'end_date': 'End date must be after start date'
                })

        return attrs


class SprintCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating sprints."""

    class Meta:
        model = Sprint
        fields = [
            'board',
            'name',
            'goal',
            'start_date',
            'end_date',
        ]

    def validate_board(self, value):
        """Validate board is Scrum type."""
        if value.board_type != BoardType.SCRUM:
            raise serializers.ValidationError(
                "Sprints can only be created for Scrum boards"
            )
        return value


class BoardStatisticsSerializer(serializers.Serializer):
    """Serializer for board statistics."""

    total_issues = serializers.IntegerField()
    backlog_count = serializers.IntegerField()
    column_counts = serializers.DictField()
    active_sprint = serializers.DictField(allow_null=True)
    velocity = serializers.FloatField(allow_null=True)


class SprintStatisticsSerializer(serializers.Serializer):
    """Serializer for sprint statistics."""

    total_issues = serializers.IntegerField()
    completed_issues = serializers.IntegerField()
    incomplete_issues = serializers.IntegerField()
    total_points = serializers.FloatField()
    completed_points = serializers.FloatField()
    remaining_points = serializers.FloatField()
    progress_percentage = serializers.FloatField()
    velocity = serializers.FloatField()
    days_remaining = serializers.IntegerField()
    duration_days = serializers.IntegerField()


class BurndownDataSerializer(serializers.Serializer):
    """Serializer for burndown chart data."""

    date = serializers.DateField()
    remaining = serializers.FloatField()
    ideal = serializers.FloatField()


class AddIssueToBoardSerializer(serializers.Serializer):
    """Serializer for adding issue to board."""

    issue_id = serializers.UUIDField()
    rank = serializers.IntegerField(required=False, allow_null=True)


class RerankIssuesSerializer(serializers.Serializer):
    """Serializer for reranking board issues."""

    issue_order = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1
    )


class AddIssueToSprintSerializer(serializers.Serializer):
    """Serializer for adding issue to sprint."""

    issue_id = serializers.UUIDField()


class BulkAddIssuesToSprintSerializer(serializers.Serializer):
    """Serializer for bulk adding issues to sprint."""

    issue_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1
    )


class MoveIssuesBetweenSprintsSerializer(serializers.Serializer):
    """Serializer for moving issues between sprints."""

    source_sprint_id = serializers.UUIDField()
    target_sprint_id = serializers.UUIDField()
    issue_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1
    )

    def validate(self, attrs):
        """Validate sprints are different."""
        if attrs['source_sprint_id'] == attrs['target_sprint_id']:
            raise serializers.ValidationError(
                "Source and target sprints must be different"
            )
        return attrs


class CompleteSprintSerializer(serializers.Serializer):
    """Serializer for completing a sprint."""

    move_incomplete_to = serializers.UUIDField(required=False, allow_null=True)


class ColumnConfigSerializer(serializers.Serializer):
    """Serializer for board column configuration."""

    columns = serializers.ListField(
        child=serializers.DictField(),
        min_length=1
    )


class SwimlaneConfigSerializer(serializers.Serializer):
    """Serializer for board swimlane configuration."""

    type = serializers.ChoiceField(
        choices=['assignee', 'priority', 'epic', 'issue_type', 'none']
    )
    config = serializers.DictField(default=dict)


class QuickFiltersSerializer(serializers.Serializer):
    """Serializer for board quick filters."""

    quick_filters = serializers.ListField(
        child=serializers.DictField(),
        min_length=0
    )
