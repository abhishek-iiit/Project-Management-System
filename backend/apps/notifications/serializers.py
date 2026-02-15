"""
Serializers for notifications.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model

from apps.notifications.models import Notification, NotificationPreference, NotificationType

User = get_user_model()


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model."""

    actor_email = serializers.EmailField(source='actor.email', read_only=True, allow_null=True)
    actor_name = serializers.SerializerMethodField()
    issue_key = serializers.CharField(source='issue.key', read_only=True, allow_null=True)
    project_key = serializers.CharField(source='project.key', read_only=True, allow_null=True)
    sprint_name = serializers.CharField(source='sprint.name', read_only=True, allow_null=True)
    is_read = serializers.BooleanField(read_only=True)
    display_text = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id',
            'organization',
            'recipient',
            'actor',
            'actor_email',
            'actor_name',
            'notification_type',
            'title',
            'message',
            'issue',
            'issue_key',
            'project',
            'project_key',
            'sprint',
            'sprint_name',
            'data',
            'action_url',
            'read_at',
            'is_read',
            'email_sent',
            'email_sent_at',
            'display_text',
            'created_at',
        ]
        read_only_fields = fields

    def get_actor_name(self, obj):
        """Get actor's display name."""
        if obj.actor:
            return obj.actor.get_full_name() or obj.actor.email
        return None

    def get_display_text(self, obj):
        """Get formatted display text."""
        return obj.get_display_text()


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for NotificationPreference model."""

    project_key = serializers.CharField(source='project.key', read_only=True, allow_null=True)

    class Meta:
        model = NotificationPreference
        fields = [
            'id',
            'organization',
            'user',
            'project',
            'project_key',
            'is_enabled',
            'in_app_enabled',
            'email_enabled',
            'push_enabled',
            'email_digest_enabled',
            'email_digest_frequency',
            'event_preferences',
            'dnd_enabled',
            'dnd_until',
            'notify_on_mention',
            'notify_on_watched_issue_update',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'user', 'organization', 'created_at', 'updated_at']


class NotificationPreferenceUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating notification preferences."""

    class Meta:
        model = NotificationPreference
        fields = [
            'is_enabled',
            'in_app_enabled',
            'email_enabled',
            'push_enabled',
            'email_digest_enabled',
            'email_digest_frequency',
            'event_preferences',
            'dnd_enabled',
            'dnd_until',
            'notify_on_mention',
            'notify_on_watched_issue_update',
        ]


class NotificationStatsSerializer(serializers.Serializer):
    """Serializer for notification statistics."""

    total_count = serializers.IntegerField()
    unread_count = serializers.IntegerField()
    read_count = serializers.IntegerField()
    by_type = serializers.DictField()
