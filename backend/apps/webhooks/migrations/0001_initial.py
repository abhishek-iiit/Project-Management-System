# Generated migration for webhooks app

import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('organizations', '0001_initial'),
        ('projects', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Webhook',
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
                    'deleted_at',
                    models.DateTimeField(
                        blank=True,
                        db_index=True,
                        help_text='Timestamp when the record was soft deleted',
                        null=True,
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
                    'name',
                    models.CharField(
                        help_text='Webhook name',
                        max_length=200,
                        verbose_name='name',
                    ),
                ),
                (
                    'description',
                    models.TextField(
                        blank=True,
                        help_text='Webhook description',
                        verbose_name='description',
                    ),
                ),
                (
                    'url',
                    models.URLField(
                        help_text='URL to send webhook requests to',
                        max_length=500,
                        verbose_name='URL',
                    ),
                ),
                (
                    'events',
                    models.JSONField(
                        default=list,
                        help_text='List of events to subscribe to',
                        verbose_name='events',
                    ),
                ),
                (
                    'secret',
                    models.CharField(
                        help_text='Secret key for HMAC signature generation',
                        max_length=128,
                        verbose_name='secret',
                    ),
                ),
                (
                    'is_active',
                    models.BooleanField(
                        db_index=True,
                        default=True,
                        help_text='Whether this webhook is active',
                        verbose_name='is active',
                    ),
                ),
                (
                    'custom_headers',
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text='Custom headers to include in webhook requests',
                        verbose_name='custom headers',
                    ),
                ),
                (
                    'max_retries',
                    models.IntegerField(
                        default=3,
                        help_text='Maximum number of retry attempts',
                        verbose_name='max retries',
                    ),
                ),
                (
                    'timeout_seconds',
                    models.IntegerField(
                        default=30,
                        help_text='Request timeout in seconds',
                        verbose_name='timeout seconds',
                    ),
                ),
                (
                    'total_deliveries',
                    models.IntegerField(
                        default=0,
                        help_text='Total number of delivery attempts',
                        verbose_name='total deliveries',
                    ),
                ),
                (
                    'successful_deliveries',
                    models.IntegerField(
                        default=0,
                        help_text='Number of successful deliveries',
                        verbose_name='successful deliveries',
                    ),
                ),
                (
                    'failed_deliveries',
                    models.IntegerField(
                        default=0,
                        help_text='Number of failed deliveries',
                        verbose_name='failed deliveries',
                    ),
                ),
                (
                    'last_delivery_at',
                    models.DateTimeField(
                        blank=True,
                        help_text='When last delivery was attempted',
                        null=True,
                        verbose_name='last delivery at',
                    ),
                ),
                (
                    'last_success_at',
                    models.DateTimeField(
                        blank=True,
                        help_text='When last successful delivery occurred',
                        null=True,
                        verbose_name='last success at',
                    ),
                ),
                (
                    'created_by',
                    models.ForeignKey(
                        blank=True,
                        help_text='User who created this webhook',
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='created_webhooks',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'organization',
                    models.ForeignKey(
                        help_text='Organization this webhook belongs to',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='webhooks',
                        to='organizations.organization',
                    ),
                ),
                (
                    'project',
                    models.ForeignKey(
                        blank=True,
                        help_text='Project this webhook applies to (null for organization-wide)',
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='webhooks',
                        to='projects.project',
                    ),
                ),
                (
                    'updated_by',
                    models.ForeignKey(
                        blank=True,
                        help_text='User who last updated this webhook',
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='updated_webhooks',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'verbose_name': 'webhook',
                'verbose_name_plural': 'webhooks',
                'db_table': 'webhooks',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='WebhookDelivery',
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
                    'event_type',
                    models.CharField(
                        db_index=True,
                        help_text='Type of event that triggered this delivery',
                        max_length=50,
                        verbose_name='event type',
                    ),
                ),
                (
                    'event_id',
                    models.UUIDField(
                        blank=True,
                        help_text='ID of the entity that triggered the event',
                        null=True,
                        verbose_name='event ID',
                    ),
                ),
                (
                    'payload',
                    models.JSONField(
                        help_text='JSON payload sent to webhook',
                        verbose_name='payload',
                    ),
                ),
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('pending', 'Pending'),
                            ('success', 'Success'),
                            ('failed', 'Failed'),
                            ('retrying', 'Retrying'),
                        ],
                        db_index=True,
                        default='pending',
                        help_text='Delivery status',
                        max_length=20,
                        verbose_name='status',
                    ),
                ),
                (
                    'request_url',
                    models.URLField(
                        help_text='URL the request was sent to',
                        max_length=500,
                        verbose_name='request URL',
                    ),
                ),
                (
                    'request_headers',
                    models.JSONField(
                        default=dict,
                        help_text='Headers sent with the request',
                        verbose_name='request headers',
                    ),
                ),
                (
                    'request_body',
                    models.TextField(
                        help_text='Request body (JSON string)',
                        verbose_name='request body',
                    ),
                ),
                (
                    'response_status_code',
                    models.IntegerField(
                        blank=True,
                        help_text='HTTP status code from response',
                        null=True,
                        verbose_name='response status code',
                    ),
                ),
                (
                    'response_headers',
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text='Headers from response',
                        verbose_name='response headers',
                    ),
                ),
                (
                    'response_body',
                    models.TextField(
                        blank=True,
                        help_text='Response body',
                        verbose_name='response body',
                    ),
                ),
                (
                    'error_message',
                    models.TextField(
                        blank=True,
                        help_text='Error message if delivery failed',
                        verbose_name='error message',
                    ),
                ),
                (
                    'error_details',
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text='Detailed error information',
                        verbose_name='error details',
                    ),
                ),
                (
                    'duration_ms',
                    models.IntegerField(
                        blank=True,
                        help_text='Request duration in milliseconds',
                        null=True,
                        verbose_name='duration (ms)',
                    ),
                ),
                (
                    'delivered_at',
                    models.DateTimeField(
                        blank=True,
                        help_text='When the delivery was completed',
                        null=True,
                        verbose_name='delivered at',
                    ),
                ),
                (
                    'retry_count',
                    models.IntegerField(
                        default=0,
                        help_text='Number of retry attempts',
                        verbose_name='retry count',
                    ),
                ),
                (
                    'next_retry_at',
                    models.DateTimeField(
                        blank=True,
                        help_text='When to retry next (if applicable)',
                        null=True,
                        verbose_name='next retry at',
                    ),
                ),
                (
                    'webhook',
                    models.ForeignKey(
                        help_text='Webhook that was delivered',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='deliveries',
                        to='webhooks.webhook',
                    ),
                ),
            ],
            options={
                'verbose_name': 'webhook delivery',
                'verbose_name_plural': 'webhook deliveries',
                'db_table': 'webhook_deliveries',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='webhook',
            index=models.Index(
                fields=['organization', 'is_active'],
                name='webhooks_organiz_4a5b6c_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='webhook',
            index=models.Index(
                fields=['project', 'is_active'],
                name='webhooks_project_7d8e9f_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='webhook',
            index=models.Index(
                fields=['is_active', '-created_at'],
                name='webhooks_is_acti_1a2b3c_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='webhookdelivery',
            index=models.Index(
                fields=['webhook', '-created_at'],
                name='webhook_de_webhook_4d5e6f_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='webhookdelivery',
            index=models.Index(
                fields=['status', '-created_at'],
                name='webhook_de_status_7g8h9i_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='webhookdelivery',
            index=models.Index(
                fields=['event_type', '-created_at'],
                name='webhook_de_event_t_1j2k3l_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='webhookdelivery',
            index=models.Index(
                fields=['-created_at'],
                name='webhook_de_created_4m5n6o_idx',
            ),
        ),
    ]
