"""
Search service for executing searches and managing filters.
"""

import time
from typing import Dict, List, Optional, Any
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.issues.models import Issue
from apps.search.models import SavedFilter, SearchHistory
from apps.search.services.jql_parser import JQLService
from apps.search.documents import ElasticsearchService


class SearchService:
    """
    Service for searching issues using JQL or full-text search.

    Handles both database queries and Elasticsearch (when available).
    """

    def __init__(self, user, organization):
        """
        Initialize search service.

        Args:
            user: Current user
            organization: Current organization
        """
        self.user = user
        self.organization = organization

    def search_issues(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        use_elasticsearch: bool = False,
    ) -> Dict[str, Any]:
        """
        Search issues using JQL query or filters.

        Args:
            query: JQL query string
            filters: Additional filters dict
            use_elasticsearch: Whether to use Elasticsearch (if available)

        Returns:
            Dict with results and metadata
        """
        start_time = time.time()

        try:
            # Use Elasticsearch if available and requested
            if use_elasticsearch and ElasticsearchService.is_available():
                results = self._search_with_elasticsearch(query, filters)
            else:
                results = self._search_with_database(query, filters)

            # Calculate execution time
            execution_time = int((time.time() - start_time) * 1000)

            # Save to search history
            self._save_to_history(
                query=query or '',
                query_type='jql' if query else 'filter',
                results_count=results['count'],
                execution_time_ms=execution_time,
            )

            results['execution_time_ms'] = execution_time
            return results

        except Exception as e:
            raise ValueError(f"Search failed: {str(e)}")

    def _search_with_database(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Search issues using database queries.

        Args:
            query: JQL query string
            filters: Additional filters dict

        Returns:
            Dict with results and metadata
        """
        # Start with base queryset
        queryset = Issue.objects.filter(
            project__organization=self.organization
        ).select_related(
            'project',
            'issue_type',
            'status',
            'priority',
            'reporter',
            'assignee',
            'epic',
            'parent',
        ).prefetch_related(
            'labels',
        )

        # Apply JQL query if provided
        if query:
            jql_q = JQLService.parse_jql(
                query,
                user=self.user,
                organization=self.organization
            )
            queryset = queryset.filter(jql_q)

        # Apply additional filters
        if filters:
            queryset = self._apply_filters(queryset, filters)

        # Get count
        count = queryset.count()

        return {
            'queryset': queryset,
            'count': count,
            'query': query,
            'filters': filters,
        }

    def _search_with_elasticsearch(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Search issues using Elasticsearch.

        Args:
            query: JQL query string
            filters: Additional filters dict

        Returns:
            Dict with results and metadata
        """
        # Use Elasticsearch service
        results = ElasticsearchService.search_issues(query, filters)

        # Convert to Issue queryset
        issue_ids = [r['id'] for r in results]
        queryset = Issue.objects.filter(id__in=issue_ids)

        return {
            'queryset': queryset,
            'count': len(results),
            'query': query,
            'filters': filters,
        }

    def _apply_filters(self, queryset: QuerySet, filters: Dict[str, Any]) -> QuerySet:
        """
        Apply additional filters to queryset.

        Args:
            queryset: Base queryset
            filters: Filters dict

        Returns:
            Filtered queryset
        """
        # Project filter
        if 'project' in filters:
            project_id = filters['project']
            queryset = queryset.filter(project_id=project_id)

        # Issue type filter
        if 'issue_type' in filters:
            issue_type_id = filters['issue_type']
            queryset = queryset.filter(issue_type_id=issue_type_id)

        # Status filter
        if 'status' in filters:
            status_id = filters['status']
            queryset = queryset.filter(status_id=status_id)

        # Priority filter
        if 'priority' in filters:
            priority_id = filters['priority']
            queryset = queryset.filter(priority_id=priority_id)

        # Assignee filter
        if 'assignee' in filters:
            assignee_id = filters['assignee']
            if assignee_id == 'currentUser':
                queryset = queryset.filter(assignee=self.user)
            elif assignee_id == 'unassigned':
                queryset = queryset.filter(assignee__isnull=True)
            else:
                queryset = queryset.filter(assignee_id=assignee_id)

        # Reporter filter
        if 'reporter' in filters:
            reporter_id = filters['reporter']
            if reporter_id == 'currentUser':
                queryset = queryset.filter(reporter=self.user)
            else:
                queryset = queryset.filter(reporter_id=reporter_id)

        # Labels filter
        if 'labels' in filters:
            labels = filters['labels']
            if isinstance(labels, list):
                queryset = queryset.filter(labels__name__in=labels).distinct()
            else:
                queryset = queryset.filter(labels__name=labels).distinct()

        # Date range filters
        if 'created_after' in filters:
            queryset = queryset.filter(created_at__gte=filters['created_after'])

        if 'created_before' in filters:
            queryset = queryset.filter(created_at__lte=filters['created_before'])

        if 'updated_after' in filters:
            queryset = queryset.filter(updated_at__gte=filters['updated_after'])

        if 'updated_before' in filters:
            queryset = queryset.filter(updated_at__lte=filters['updated_before'])

        # Full-text search
        if 'text' in filters:
            text = filters['text']
            q = Q()
            q |= Q(summary__icontains=text)
            q |= Q(description__icontains=text)
            q |= Q(key__icontains=text)
            queryset = queryset.filter(q)

        return queryset

    def _save_to_history(
        self,
        query: str,
        query_type: str,
        results_count: int,
        execution_time_ms: int,
    ):
        """
        Save search to history.

        Args:
            query: Search query
            query_type: Type of query (jql, fulltext)
            results_count: Number of results
            execution_time_ms: Execution time in milliseconds
        """
        try:
            SearchHistory.objects.create(
                organization=self.organization,
                user=self.user,
                query=query,
                query_type=query_type,
                results_count=results_count,
                execution_time_ms=execution_time_ms,
            )
        except Exception:
            # Don't fail the search if history save fails
            pass

    def get_autocomplete_suggestions(self, field: str, query: str, limit: int = 10) -> List[str]:
        """
        Get autocomplete suggestions for a field.

        Args:
            field: Field name (e.g., 'assignee', 'reporter', 'labels')
            query: Partial query string
            limit: Maximum number of suggestions

        Returns:
            List of suggestions
        """
        suggestions = []

        if field == 'assignee' or field == 'reporter':
            # Get users from organization
            from apps.organizations.models import OrganizationMember
            members = OrganizationMember.objects.filter(
                organization=self.organization,
                user__email__icontains=query,
            ).select_related('user')[:limit]
            suggestions = [m.user.email for m in members]

        elif field == 'labels':
            # Get labels from issues
            from apps.issues.models import Label
            labels = Label.objects.filter(
                name__icontains=query,
                issues__project__organization=self.organization,
            ).distinct()[:limit]
            suggestions = [label.name for label in labels]

        elif field == 'project':
            # Get projects
            from apps.projects.models import Project
            projects = Project.objects.filter(
                organization=self.organization,
                key__icontains=query,
            )[:limit]
            suggestions = [p.key for p in projects]

        elif field == 'status':
            # Get statuses
            from apps.workflows.models import Status
            statuses = Status.objects.filter(
                organization=self.organization,
                name__icontains=query,
            )[:limit]
            suggestions = [s.name for s in statuses]

        elif field == 'priority':
            # Get priorities
            from apps.issues.models import Priority
            priorities = Priority.objects.filter(
                organization=self.organization,
                name__icontains=query,
            )[:limit]
            suggestions = [p.name for p in priorities]

        return suggestions

    def validate_jql(self, query: str) -> Dict[str, Any]:
        """
        Validate JQL query syntax.

        Args:
            query: JQL query string

        Returns:
            Dict with validation result
        """
        is_valid, error_message = JQLService.validate_jql(query)
        return {
            'is_valid': is_valid,
            'error_message': error_message,
        }


class SavedFilterService:
    """Service for managing saved filters."""

    def __init__(self, user, organization):
        """
        Initialize saved filter service.

        Args:
            user: Current user
            organization: Current organization
        """
        self.user = user
        self.organization = organization

    def create_filter(
        self,
        name: str,
        jql: str,
        description: str = '',
        project=None,
        is_shared: bool = False,
        is_favorite: bool = False,
        config: Optional[Dict] = None,
    ) -> SavedFilter:
        """
        Create a new saved filter.

        Args:
            name: Filter name
            jql: JQL query
            description: Filter description
            project: Optional project
            is_shared: Whether filter is shared
            is_favorite: Whether filter is favorite
            config: Additional configuration

        Returns:
            Created SavedFilter instance

        Raises:
            ValueError: If JQL is invalid
        """
        # Validate JQL
        is_valid, error = JQLService.validate_jql(jql)
        if not is_valid:
            raise ValueError(f"Invalid JQL: {error}")

        # Create filter
        saved_filter = SavedFilter.objects.create(
            organization=self.organization,
            project=project,
            name=name,
            description=description,
            jql=jql,
            is_shared=is_shared,
            is_favorite=is_favorite,
            config=config or {},
            created_by=self.user,
            updated_by=self.user,
        )

        return saved_filter

    def update_filter(
        self,
        filter_id: str,
        **kwargs
    ) -> SavedFilter:
        """
        Update a saved filter.

        Args:
            filter_id: Filter ID
            **kwargs: Fields to update

        Returns:
            Updated SavedFilter instance

        Raises:
            SavedFilter.DoesNotExist: If filter not found
            ValueError: If JQL is invalid
        """
        saved_filter = SavedFilter.objects.get(
            id=filter_id,
            organization=self.organization,
        )

        # Validate JQL if being updated
        if 'jql' in kwargs:
            is_valid, error = JQLService.validate_jql(kwargs['jql'])
            if not is_valid:
                raise ValueError(f"Invalid JQL: {error}")

        # Update fields
        for key, value in kwargs.items():
            setattr(saved_filter, key, value)

        saved_filter.updated_by = self.user
        saved_filter.save()

        return saved_filter

    def delete_filter(self, filter_id: str):
        """
        Delete a saved filter (soft delete).

        Args:
            filter_id: Filter ID

        Raises:
            SavedFilter.DoesNotExist: If filter not found
        """
        saved_filter = SavedFilter.objects.get(
            id=filter_id,
            organization=self.organization,
        )
        saved_filter.deleted_at = timezone.now()
        saved_filter.save()

    def get_user_filters(self, include_shared: bool = True) -> QuerySet:
        """
        Get filters for current user.

        Args:
            include_shared: Whether to include shared filters

        Returns:
            QuerySet of SavedFilter objects
        """
        queryset = SavedFilter.objects.for_organization(
            self.organization
        ).active().with_full_details()

        if include_shared:
            # User's own filters + shared filters
            queryset = queryset.filter(
                Q(created_by=self.user) | Q(is_shared=True)
            )
        else:
            # Only user's own filters
            queryset = queryset.filter(created_by=self.user)

        return queryset

    def clone_filter(self, filter_id: str, name: Optional[str] = None) -> SavedFilter:
        """
        Clone a saved filter.

        Args:
            filter_id: Filter ID to clone
            name: Optional name for cloned filter

        Returns:
            Cloned SavedFilter instance

        Raises:
            SavedFilter.DoesNotExist: If filter not found
        """
        original_filter = SavedFilter.objects.get(
            id=filter_id,
            organization=self.organization,
        )

        return original_filter.clone(self.user, name=name)

    def mark_as_favorite(self, filter_id: str, is_favorite: bool = True):
        """
        Mark filter as favorite or unfavorite.

        Args:
            filter_id: Filter ID
            is_favorite: Whether to mark as favorite

        Raises:
            SavedFilter.DoesNotExist: If filter not found
        """
        saved_filter = SavedFilter.objects.get(
            id=filter_id,
            organization=self.organization,
        )
        saved_filter.is_favorite = is_favorite
        saved_filter.save(update_fields=['is_favorite'])
