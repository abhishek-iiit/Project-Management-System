# Generated migration for audit app

import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.contrib.postgres.fields import ArrayField


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('organizations', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditLog',
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
                    'action',
                    models.CharField(
                        choices=[
                            ('create', 'Create'),
                            ('read', 'Read'),
                            ('update', 'Update'),
                            ('delete', 'Delete'),
                            ('login', 'Login'),
                            ('logout', 'Logout'),
                            ('login_failed', 'Login Failed'),
                            ('transition', 'Transition'),
                            ('assign', 'Assign'),
                            ('comment', 'Comment'),
                            ('attach', 'Attach'),
                            ('link', 'Link'),
                            ('watch', 'Watch'),
                            ('unwatch', 'Unwatch'),
                            ('permission_grant', 'Permission Grant'),
                            ('permission_revoke', 'Permission Revoke'),
                            ('export', 'Export'),
                            ('import', 'Import'),
                        ],
                        db_index=True,
                        help_text='Type of action performed',
                        max_length=50,
                        verbose_name='action',
                    ),
                ),
                (
                    'entity_type',
                    models.CharField(
                        db_index=True,
                        help_text='Type of entity affected (e.g., Issue, Project)',
                        max_length=100,
                        verbose_name='entity type',
                    ),
                ),
                (
                    'entity_id',
                    models.UUIDField(
                        blank=True,
                        db_index=True,
                        help_text='ID of the affected entity',
                        null=True,
                        verbose_name='entity ID',
                    ),
                ),
                (
                    'entity_name',
                    models.CharField(
                        blank=True,
                        help_text='Name/identifier of the affected entity',
                        max_length=255,
                        verbose_name='entity name',
                    ),
                ),
                (
                    'changes',
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text='Field-level changes (old vs new values)',
                        verbose_name='changes',
                    ),
                ),
                (
                    'metadata',
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text='Additional metadata about the action',
                        verbose_name='metadata',
                    ),
                ),
                (
                    'ip_address',
                    models.GenericIPAddressField(
                        blank=True,
                        help_text='IP address of the request',
                        null=True,
                        verbose_name='IP address',
                    ),
                ),
                (
                    'user_agent',
                    models.TextField(
                        blank=True,
                        help_text='User agent string from the request',
                        verbose_name='user agent',
                    ),
                ),
                (
                    'request_method',
                    models.CharField(
                        blank=True,
                        help_text='HTTP request method (GET, POST, etc.)',
                        max_length=10,
                        verbose_name='request method',
                    ),
                ),
                (
                    'request_path',
                    models.CharField(
                        blank=True,
                        help_text='URL path of the request',
                        max_length=500,
                        verbose_name='request path',
                    ),
                ),
                (
                    'success',
                    models.BooleanField(
                        db_index=True,
                        default=True,
                        help_text='Whether the action succeeded',
                        verbose_name='success',
                    ),
                ),
                (
                    'error_message',
                    models.TextField(
                        blank=True,
                        help_text='Error message if action failed',
                        verbose_name='error message',
                    ),
                ),
                (
                    'duration_ms',
                    models.IntegerField(
                        blank=True,
                        help_text='Duration of the operation in milliseconds',
                        null=True,
                        verbose_name='duration (ms)',
                    ),
                ),
                (
                    'tags',
                    ArrayField(
                        models.CharField(max_length=50),
                        blank=True,
                        default=list,
                        help_text='Tags for categorizing logs',
                        verbose_name='tags',
                    ),
                ),
                (
                    'organization',
                    models.ForeignKey(
                        blank=True,
                        help_text='Organization this log belongs to',
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='audit_logs',
                        to='organizations.organization',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        blank=True,
                        help_text='User who performed the action',
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='audit_logs',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'verbose_name': 'audit log',
                'verbose_name_plural': 'audit logs',
                'db_table': 'audit_logs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(
                fields=['organization', '-created_at'],
                name='audit_logs_organiz_4a5b6c_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(
                fields=['user', '-created_at'],
                name='audit_logs_user_id_7d8e9f_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(
                fields=['entity_type', 'entity_id', '-created_at'],
                name='audit_logs_entity__1a2b3c_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(
                fields=['action', '-created_at'],
                name='audit_logs_action_4d5e6f_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(
                fields=['success', '-created_at'],
                name='audit_logs_success_7g8h9i_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(
                fields=['-created_at'],
                name='audit_logs_created_1j2k3l_idx',
            ),
        ),
    ]
