# Generated migration for search app

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
            name='SavedFilter',
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
                        help_text='Filter name',
                        max_length=200,
                        verbose_name='name',
                    ),
                ),
                (
                    'description',
                    models.TextField(
                        blank=True,
                        help_text='Filter description',
                        verbose_name='description',
                    ),
                ),
                (
                    'jql',
                    models.TextField(
                        help_text='JQL query string',
                        verbose_name='JQL query',
                    ),
                ),
                (
                    'is_shared',
                    models.BooleanField(
                        db_index=True,
                        default=False,
                        help_text='Whether this filter is shared with others',
                        verbose_name='is shared',
                    ),
                ),
                (
                    'is_favorite',
                    models.BooleanField(
                        db_index=True,
                        default=False,
                        help_text='Whether this is a favorite filter',
                        verbose_name='is favorite',
                    ),
                ),
                (
                    'usage_count',
                    models.IntegerField(
                        default=0,
                        help_text='Number of times this filter has been used',
                        verbose_name='usage count',
                    ),
                ),
                (
                    'last_used_at',
                    models.DateTimeField(
                        blank=True,
                        help_text='When this filter was last used',
                        null=True,
                        verbose_name='last used at',
                    ),
                ),
                (
                    'config',
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text='Additional filter configuration (columns, sorting, etc.)',
                        verbose_name='configuration',
                    ),
                ),
                (
                    'created_by',
                    models.ForeignKey(
                        blank=True,
                        help_text='User who created this filter',
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='created_saved_filters',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'organization',
                    models.ForeignKey(
                        help_text='Organization this filter belongs to',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='saved_filters',
                        to='organizations.organization',
                    ),
                ),
                (
                    'project',
                    models.ForeignKey(
                        blank=True,
                        help_text='Project this filter applies to (null for organization-wide)',
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='saved_filters',
                        to='projects.project',
                    ),
                ),
                (
                    'updated_by',
                    models.ForeignKey(
                        blank=True,
                        help_text='User who last updated this filter',
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='updated_saved_filters',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'verbose_name': 'saved filter',
                'verbose_name_plural': 'saved filters',
                'db_table': 'saved_filters',
                'ordering': ['-is_favorite', '-usage_count', 'name'],
            },
        ),
        migrations.CreateModel(
            name='SearchHistory',
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
                    'query',
                    models.TextField(
                        help_text='Search query (JQL or full-text)',
                        verbose_name='search query',
                    ),
                ),
                (
                    'query_type',
                    models.CharField(
                        choices=[
                            ('jql', 'JQL Query'),
                            ('fulltext', 'Full-text Search'),
                        ],
                        db_index=True,
                        default='jql',
                        help_text='Type of search query',
                        max_length=20,
                        verbose_name='query type',
                    ),
                ),
                (
                    'results_count',
                    models.IntegerField(
                        default=0,
                        help_text='Number of results returned',
                        verbose_name='results count',
                    ),
                ),
                (
                    'execution_time_ms',
                    models.IntegerField(
                        blank=True,
                        help_text='Query execution time in milliseconds',
                        null=True,
                        verbose_name='execution time (ms)',
                    ),
                ),
                (
                    'organization',
                    models.ForeignKey(
                        help_text='Organization this search belongs to',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='search_history',
                        to='organizations.organization',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        help_text='User who performed the search',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='search_history',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'verbose_name': 'search history',
                'verbose_name_plural': 'search history',
                'db_table': 'search_history',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='savedfilter',
            index=models.Index(
                fields=['organization', 'is_shared'],
                name='saved_filte_organiz_4a2c5d_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='savedfilter',
            index=models.Index(
                fields=['project', 'is_shared'],
                name='saved_filte_project_8b3d1e_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='savedfilter',
            index=models.Index(
                fields=['created_by', '-created_at'],
                name='saved_filte_created_9c4e2f_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='savedfilter',
            index=models.Index(
                fields=['-usage_count'],
                name='saved_filte_usage_c_5d6f3a_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='searchhistory',
            index=models.Index(
                fields=['user', '-created_at'],
                name='search_hist_user_id_1a2b3c_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='searchhistory',
            index=models.Index(
                fields=['organization', '-created_at'],
                name='search_hist_organiz_4d5e6f_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='searchhistory',
            index=models.Index(
                fields=['query_type', '-created_at'],
                name='search_hist_query_t_7g8h9i_idx',
            ),
        ),
    ]
