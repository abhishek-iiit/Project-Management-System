# Generated migration for notifications app

import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('organizations', '0001_initial'),
        ('projects', '0001_initial'),
        ('issues', '0001_initial'),
        ('boards', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                (
                    'created_at',
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text='Timestamp when the record was created'
                    ),
                ),
                (
                    'updated_at',
                    models.DateTimeField(
                        auto_now=True,
                        db_index=True,
                        help_text='Timestamp when the record was last updated'
                    ),
                ),
                (
                    'id',
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text='Unique identifier (UUID4)',
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    'notification_type',
                    models.CharField(
                        choices=[
                            ('issue_created', 'Issue Created'),
                            ('issue_updated', 'Issue Updated'),
                            ('issue_assigned', 'Issue Assigned'),
                            ('issue_commented', 'Issue Commented'),
                            ('issue_transitioned', 'Issue Transitioned'),
                            ('issue_mentioned', 'Mentioned in Issue'),
                            ('sprint_started', 'Sprint Started'),
                            ('sprint_completed', 'Sprint Completed'),
                            ('sprint_issue_added', 'Issue Added to Sprint'),
                            ('project_member_added', 'Added to Project'),
                            ('project_member_removed', 'Removed from Project'),
                            ('automation_executed', 'Automation Rule Executed'),
                            ('system_announcement', 'System Announcement'),
                        ],
                        db_index=True,
                        help_text='Type of notification',
                        max_length=50,
                        verbose_name='notification type',
                    ),
                ),
                (
                    'title',
                    models.CharField(
                        help_text='Notification title',
                        max_length=255,
                        verbose_name='title',
                    ),
                ),
                (
                    'message',
                    models.TextField(
                        help_text='Notification message',
                        verbose_name='message',
                    ),
                ),
                (
                    'data',
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text='Additional notification data',
                        verbose_name='data',
                    ),
                ),
                (
                    'action_url',
                    models.CharField(
                        blank=True,
                        help_text='URL to navigate when notification is clicked',
                        max_length=500,
                        verbose_name='action URL',
                    ),
                ),
                (
                    'read_at',
                    models.DateTimeField(
                        blank=True,
                        db_index=True,
                        help_text='When this notification was read',
                        null=True,
                        verbose_name='read at',
                    ),
                ),
                (
                    'email_sent',
                    models.BooleanField(
                        db_index=True,
                        default=False,
                        help_text='Whether email notification was sent',
                        verbose_name='email sent',
                    ),
                ),
                (
                    'email_sent_at',
                    models.DateTimeField(
                        blank=True,
                        help_text='When email notification was sent',
                        null=True,
                        verbose_name='email sent at',
                    ),
                ),
                (
                    'actor',
                    models.ForeignKey(
                        blank=True,
                        help_text='User who triggered this notification',
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='triggered_notifications',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'issue',
                    models.ForeignKey(
                        blank=True,
                        help_text='Related issue',
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='notifications',
                        to='issues.issue',
                    ),
                ),
                (
                    'organization',
                    models.ForeignKey(
                        help_text='Organization this notification belongs to',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='notifications',
                        to='organizations.organization',
                    ),
                ),
                (
                    'project',
                    models.ForeignKey(
                        blank=True,
                        help_text='Related project',
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='notifications',
                        to='projects.project',
                    ),
                ),
                (
                    'recipient',
                    models.ForeignKey(
                        help_text='User who receives this notification',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='notifications',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'sprint',
                    models.ForeignKey(
                        blank=True,
                        help_text='Related sprint',
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='notifications',
                        to='boards.sprint',
                    ),
                ),
            ],
            options={
                'verbose_name': 'notification',
                'verbose_name_plural': 'notifications',
                'db_table': 'notifications',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='NotificationPreference',
            fields=[
                (
                    'created_at',
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text='Timestamp when the record was created'
                    ),
                ),
                (
                    'updated_at',
                    models.DateTimeField(
                        auto_now=True,
                        db_index=True,
                        help_text='Timestamp when the record was last updated'
                    ),
                ),
                (
                    'id',
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text='Unique identifier (UUID4)',
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    'is_enabled',
                    models.BooleanField(
                        db_index=True,
                        default=True,
                        help_text='Master switch for all notifications',
                        verbose_name='is enabled',
                    ),
                ),
                (
                    'in_app_enabled',
                    models.BooleanField(
                        default=True,
                        help_text='Receive in-app notifications',
                        verbose_name='in-app enabled',
                    ),
                ),
                (
                    'email_enabled',
                    models.BooleanField(
                        default=True,
                        help_text='Receive email notifications',
                        verbose_name='email enabled',
                    ),
                ),
                (
                    'push_enabled',
                    models.BooleanField(
                        default=False,
                        help_text='Receive push notifications',
                        verbose_name='push enabled',
                    ),
                ),
                (
                    'email_digest_enabled',
                    models.BooleanField(
                        default=False,
                        help_text='Receive digest emails instead of individual emails',
                        verbose_name='email digest enabled',
                    ),
                ),
                (
                    'email_digest_frequency',
                    models.CharField(
                        choices=[
                            ('daily', 'Daily'),
                            ('weekly', 'Weekly'),
                            ('never', 'Never'),
                        ],
                        default='daily',
                        help_text='How often to send digest emails',
                        max_length=20,
                        verbose_name='email digest frequency',
                    ),
                ),
                (
                    'event_preferences',
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text='Per-event notification preferences',
                        verbose_name='event preferences',
                    ),
                ),
                (
                    'dnd_enabled',
                    models.BooleanField(
                        default=False,
                        help_text='Temporarily disable all notifications',
                        verbose_name='do not disturb',
                    ),
                ),
                (
                    'dnd_until',
                    models.DateTimeField(
                        blank=True,
                        help_text='When to re-enable notifications',
                        null=True,
                        verbose_name='do not disturb until',
                    ),
                ),
                (
                    'notify_on_mention',
                    models.BooleanField(
                        default=True,
                        help_text='Receive notifications when mentioned',
                        verbose_name='notify on mention',
                    ),
                ),
                (
                    'notify_on_watched_issue_update',
                    models.BooleanField(
                        default=True,
                        help_text='Receive notifications for watched issues',
                        verbose_name='notify on watched issue update',
                    ),
                ),
                (
                    'organization',
                    models.ForeignKey(
                        help_text='Organization these preferences belong to',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='notification_preferences',
                        to='organizations.organization',
                    ),
                ),
                (
                    'project',
                    models.ForeignKey(
                        blank=True,
                        help_text='Project-specific preferences (null for global)',
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='notification_preferences',
                        to='projects.project',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        help_text='User who owns these preferences',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='notification_preferences',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'verbose_name': 'notification preference',
                'verbose_name_plural': 'notification preferences',
                'db_table': 'notification_preferences',
                'ordering': ['user', 'organization'],
            },
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(
                fields=['recipient', '-created_at'],
                name='notificati_recipie_4a5b6c_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(
                fields=['recipient', 'read_at'],
                name='notificati_recipie_7d8e9f_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(
                fields=['organization', '-created_at'],
                name='notificati_organiz_1a2b3c_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(
                fields=['notification_type', '-created_at'],
                name='notificati_notific_4d5e6f_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(
                fields=['issue', '-created_at'],
                name='notificati_issue_i_7g8h9i_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='notificationpreference',
            index=models.Index(
                fields=['user', 'organization'],
                name='notificati_user_id_1j2k3l_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='notificationpreference',
            index=models.Index(
                fields=['organization', 'is_enabled'],
                name='notificati_organiz_4m5n6o_idx',
            ),
        ),
        migrations.AlterUniqueTogether(
            name='notificationpreference',
            unique_together={('user', 'organization', 'project')},
        ),
    ]
