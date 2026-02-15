"""
Serializers for audit logs.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model

from apps.audit.models import AuditLog

User = get_user_model()


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for AuditLog model."""

    user_email = serializers.EmailField(source='user.email', read_only=True, allow_null=True)
    user_name = serializers.SerializerMethodField()
    organization_name = serializers.CharField(source='organization.name', read_only=True, allow_null=True)
    changed_fields = serializers.SerializerMethodField()
    change_summary = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            'id',
            'organization',
            'organization_name',
            'user',
            'user_email',
            'user_name',
            'action',
            'entity_type',
            'entity_id',
            'entity_name',
            'changes',
            'changed_fields',
            'change_summary',
            'metadata',
            'ip_address',
            'user_agent',
            'request_method',
            'request_path',
            'success',
            'error_message',
            'duration_ms',
            'tags',
            'created_at',
        ]
        read_only_fields = fields

    def get_user_name(self, obj):
        """Get user's display name."""
        if obj.user:
            return obj.user.get_full_name() or obj.user.email
        return 'System'

    def get_changed_fields(self, obj):
        """Get list of changed field names."""
        return obj.get_changed_fields()

    def get_change_summary(self, obj):
        """Get change summary."""
        return obj.get_change_summary()


class AuditLogListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing audit logs."""

    user_email = serializers.EmailField(source='user.email', read_only=True, allow_null=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True, allow_null=True)
    change_summary = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            'id',
            'organization_name',
            'user_email',
            'action',
            'entity_type',
            'entity_name',
            'change_summary',
            'success',
            'created_at',
        ]

    def get_change_summary(self, obj):
        """Get change summary."""
        return obj.get_change_summary()


class AuditStatsSerializer(serializers.Serializer):
    """Serializer for audit statistics."""

    total_logs = serializers.IntegerField()
    successful_logs = serializers.IntegerField()
    failed_logs = serializers.IntegerField()
    by_action = serializers.DictField()
    by_entity_type = serializers.DictField()
    by_user = serializers.ListField()
    recent_activity = AuditLogListSerializer(many=True)
