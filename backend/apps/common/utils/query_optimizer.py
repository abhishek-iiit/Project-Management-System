"""
Query optimization utilities.

Following CLAUDE.md best practices for query optimization.
"""

from typing import List, Optional
from django.db.models import QuerySet, Prefetch


def optimize_queryset(
    queryset: QuerySet,
    select_related_fields: Optional[List[str]] = None,
    prefetch_related_fields: Optional[List[str]] = None
) -> QuerySet:
    """
    Optimize queryset with select_related and prefetch_related.

    Args:
        queryset: Base queryset to optimize
        select_related_fields: Fields for select_related (ForeignKey, OneToOne)
        prefetch_related_fields: Fields for prefetch_related (ManyToMany, reverse FK)

    Returns:
        Optimized queryset

    Example:
        queryset = optimize_queryset(
            Issue.objects.all(),
            select_related_fields=['project', 'assignee', 'reporter'],
            prefetch_related_fields=['comments', 'attachments', 'watchers']
        )
    """
    if select_related_fields:
        queryset = queryset.select_related(*select_related_fields)

    if prefetch_related_fields:
        queryset = queryset.prefetch_related(*prefetch_related_fields)

    return queryset


def detect_n_plus_one(queryset: QuerySet, max_queries: int = 10):
    """
    Helper to detect N+1 query problems during development.

    Args:
        queryset: Queryset to check
        max_queries: Maximum allowed queries

    Raises:
        Warning: If too many queries detected
    """
    from django.test.utils import override_settings
    from django.db import connection
    from django.conf import settings

    if not settings.DEBUG:
        return

    # Reset queries
    connection.queries_log.clear()

    # Execute queryset
    list(queryset)

    # Check query count
    query_count = len(connection.queries)
    if query_count > max_queries:
        import warnings
        warnings.warn(
            f"Potential N+1 query problem detected: {query_count} queries executed. "
            f"Expected <= {max_queries}",
            RuntimeWarning
        )


class QuerySetOptimizer:
    """
    Context manager for query optimization tracking.

    Usage:
        with QuerySetOptimizer() as optimizer:
            issues = Issue.objects.all()
            for issue in issues:
                print(issue.project.name)  # Will detect N+1
        print(f"Queries executed: {optimizer.query_count}")
    """

    def __init__(self):
        self.query_count = 0
        self.queries = []

    def __enter__(self):
        from django.db import connection
        from django.conf import settings

        if settings.DEBUG:
            connection.queries_log.clear()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        from django.db import connection
        from django.conf import settings

        if settings.DEBUG:
            self.queries = connection.queries
            self.query_count = len(self.queries)
