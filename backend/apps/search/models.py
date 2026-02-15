"""
Search models for saved filters and search history.
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimestampedModel, SoftDeleteModel

User = get_user_model()


class SavedFilterQuerySet(models.QuerySet):
    """Custom QuerySet for SavedFilter."""

    def active(self):
        """Filter active saved filters only."""
        return self.filter(deleted_at__isnull=True)

    def for_user(self, user):
        """Filter saved filters for a specific user."""
        return self.filter(created_by=user)

    def for_organization(self, organization):
        """Filter saved filters for an organization."""
        return self.filter(organization=organization)

    def shared(self):
        """Filter shared saved filters only."""
        return self.filter(is_shared=True)

    def with_full_details(self):
        """Optimize query with all related data."""
        return self.select_related(
            'organization',
            'project',
            'created_by',
            'updated_by',
        )


class SavedFilter(TimestampedModel, SoftDeleteModel):
    """
    Saved search filter model.

    Allows users to save JQL queries for quick access and sharing.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text=_('Unique identifier (UUID4)')
    )

    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='saved_filters',
        help_text=_('Organization this filter belongs to')
    )

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='saved_filters',
        null=True,
        blank=True,
        help_text=_('Project this filter applies to (null for organization-wide)')
    )

    name = models.CharField(
        max_length=200,
        verbose_name=_('name'),
        help_text=_('Filter name')
    )

    description = models.TextField(
        blank=True,
        verbose_name=_('description'),
        help_text=_('Filter description')
    )

    jql = models.TextField(
        verbose_name=_('JQL query'),
        help_text=_('JQL query string')
    )

    is_shared = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=_('is shared'),
        help_text=_('Whether this filter is shared with others')
    )

    is_favorite = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=_('is favorite'),
        help_text=_('Whether this is a favorite filter')
    )

    usage_count = models.IntegerField(
        default=0,
        verbose_name=_('usage count'),
        help_text=_('Number of times this filter has been used')
    )

    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('last used at'),
        help_text=_('When this filter was last used')
    )

    config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('configuration'),
        help_text=_('Additional filter configuration (columns, sorting, etc.)')
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_saved_filters',
        help_text=_('User who created this filter')
    )

    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_saved_filters',
        help_text=_('User who last updated this filter')
    )

    objects = SavedFilterQuerySet.as_manager()

    class Meta:
        db_table = 'saved_filters'
        verbose_name = _('saved filter')
        verbose_name_plural = _('saved filters')
        ordering = ['-is_favorite', '-usage_count', 'name']
        indexes = [
            models.Index(fields=['organization', 'is_shared']),
            models.Index(fields=['project', 'is_shared']),
            models.Index(fields=['created_by', '-created_at']),
            models.Index(fields=['-usage_count']),
        ]

    def __str__(self):
        return f"{self.name} ({self.organization.name})"

    def increment_usage(self):
        """Increment usage count and update last used timestamp."""
        from django.utils import timezone
        self.usage_count += 1
        self.last_used_at = timezone.now()
        self.save(update_fields=['usage_count', 'last_used_at'])

    def clone(self, user, name=None):
        """
        Clone this filter for another user.

        Args:
            user: User who will own the cloned filter
            name: Optional name for the cloned filter

        Returns:
            Cloned SavedFilter instance
        """
        cloned_filter = SavedFilter.objects.create(
            organization=self.organization,
            project=self.project,
            name=name or f"Copy of {self.name}",
            description=self.description,
            jql=self.jql,
            is_shared=False,
            config=self.config.copy(),
            created_by=user,
            updated_by=user,
        )
        return cloned_filter


class SearchHistoryQuerySet(models.QuerySet):
    """Custom QuerySet for SearchHistory."""

    def for_user(self, user):
        """Filter search history for a specific user."""
        return self.filter(user=user)

    def for_organization(self, organization):
        """Filter search history for an organization."""
        return self.filter(organization=organization)

    def recent(self, limit=10):
        """Get recent searches."""
        return self.order_by('-created_at')[:limit]


class SearchHistory(TimestampedModel):
    """
    Search history model to track user searches.

    Used for search autocomplete and analytics.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text=_('Unique identifier (UUID4)')
    )

    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='search_history',
        help_text=_('Organization this search belongs to')
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='search_history',
        help_text=_('User who performed the search')
    )

    query = models.TextField(
        verbose_name=_('search query'),
        help_text=_('Search query (JQL or full-text)')
    )

    query_type = models.CharField(
        max_length=20,
        choices=[
            ('jql', _('JQL Query')),
            ('fulltext', _('Full-text Search')),
        ],
        default='jql',
        db_index=True,
        verbose_name=_('query type'),
        help_text=_('Type of search query')
    )

    results_count = models.IntegerField(
        default=0,
        verbose_name=_('results count'),
        help_text=_('Number of results returned')
    )

    execution_time_ms = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('execution time (ms)'),
        help_text=_('Query execution time in milliseconds')
    )

    objects = SearchHistoryQuerySet.as_manager()

    class Meta:
        db_table = 'search_history'
        verbose_name = _('search history')
        verbose_name_plural = _('search history')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['organization', '-created_at']),
            models.Index(fields=['query_type', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.query[:50]}"
