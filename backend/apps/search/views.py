"""
Views for search and saved filters.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Avg, Count, Q

from apps.search.models import SavedFilter, SearchHistory
from apps.search.serializers import (
    SavedFilterSerializer,
    SavedFilterCreateSerializer,
    SavedFilterUpdateSerializer,
    SavedFilterListSerializer,
    SavedFilterCloneSerializer,
    SearchHistorySerializer,
    JQLValidationSerializer,
    JQLValidationResponseSerializer,
    SearchRequestSerializer,
    AutocompleteRequestSerializer,
    AutocompleteResponseSerializer,
    SearchStatsSerializer,
)
from apps.search.services.search_service import SearchService, SavedFilterService
from apps.issues.serializers import IssueSerializer


class SavedFilterViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing saved filters.

    Endpoints:
        GET    /saved-filters/               - List filters
        POST   /saved-filters/               - Create filter
        GET    /saved-filters/{id}/          - Retrieve filter
        PUT    /saved-filters/{id}/          - Update filter
        DELETE /saved-filters/{id}/          - Delete filter (soft delete)
        POST   /saved-filters/{id}/clone/    - Clone filter
        POST   /saved-filters/{id}/favorite/ - Mark as favorite
        POST   /saved-filters/{id}/execute/  - Execute filter and get results
    """

    permission_classes = [IsAuthenticated]
    queryset = SavedFilter.objects.all()

    def get_queryset(self):
        """Get queryset filtered by organization."""
        user = self.request.user
        organization = getattr(user, 'current_organization', None)

        if not organization:
            return SavedFilter.objects.none()

        queryset = SavedFilter.objects.for_organization(organization).active()

        # Filter by user if requested
        if self.request.query_params.get('my_filters') == 'true':
            queryset = queryset.filter(created_by=user)
        else:
            # Show user's own filters + shared filters
            queryset = queryset.filter(
                Q(created_by=user) | Q(is_shared=True)
            )

        # Filter by project if provided
        project_id = self.request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(
                Q(project_id=project_id) | Q(project__isnull=True)
            )

        # Filter favorites
        if self.request.query_params.get('favorites') == 'true':
            queryset = queryset.filter(is_favorite=True)

        return queryset.with_full_details()

    def get_serializer_class(self):
        """Get appropriate serializer class."""
        if self.action == 'list':
            return SavedFilterListSerializer
        elif self.action == 'create':
            return SavedFilterCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return SavedFilterUpdateSerializer
        return SavedFilterSerializer

    def perform_create(self, serializer):
        """Create a new saved filter."""
        user = self.request.user
        organization = getattr(user, 'current_organization', None)

        service = SavedFilterService(user=user, organization=organization)
        saved_filter = service.create_filter(
            **serializer.validated_data,
            created_by=user,
            updated_by=user,
        )
        return saved_filter

    def create(self, request, *args, **kwargs):
        """Create a new saved filter."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        saved_filter = self.perform_create(serializer)

        output_serializer = SavedFilterSerializer(saved_filter)
        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED
        )

    def perform_update(self, serializer):
        """Update a saved filter."""
        user = self.request.user
        organization = getattr(user, 'current_organization', None)

        service = SavedFilterService(user=user, organization=organization)
        saved_filter = service.update_filter(
            filter_id=self.get_object().id,
            **serializer.validated_data
        )
        return saved_filter

    def update(self, request, *args, **kwargs):
        """Update a saved filter."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        saved_filter = self.perform_update(serializer)

        output_serializer = SavedFilterSerializer(saved_filter)
        return Response(output_serializer.data)

    def destroy(self, request, *args, **kwargs):
        """Delete a saved filter (soft delete)."""
        user = self.request.user
        organization = getattr(user, 'current_organization', None)

        service = SavedFilterService(user=user, organization=organization)
        service.delete_filter(filter_id=self.get_object().id)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        """Clone a saved filter."""
        user = self.request.user
        organization = getattr(user, 'current_organization', None)

        serializer = SavedFilterCloneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = SavedFilterService(user=user, organization=organization)
        cloned_filter = service.clone_filter(
            filter_id=pk,
            name=serializer.validated_data.get('name')
        )

        output_serializer = SavedFilterSerializer(cloned_filter)
        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def favorite(self, request, pk=None):
        """Mark filter as favorite or unfavorite."""
        user = self.request.user
        organization = getattr(user, 'current_organization', None)

        is_favorite = request.data.get('is_favorite', True)

        service = SavedFilterService(user=user, organization=organization)
        service.mark_as_favorite(filter_id=pk, is_favorite=is_favorite)

        saved_filter = self.get_object()
        serializer = SavedFilterSerializer(saved_filter)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """Execute the filter and return issues."""
        user = self.request.user
        organization = getattr(user, 'current_organization', None)

        saved_filter = self.get_object()

        # Increment usage count
        saved_filter.increment_usage()

        # Execute search
        search_service = SearchService(user=user, organization=organization)
        results = search_service.search_issues(query=saved_filter.jql)

        # Paginate results
        queryset = results['queryset']
        page = self.paginate_queryset(queryset)

        if page is not None:
            issue_serializer = IssueSerializer(page, many=True)
            return self.get_paginated_response({
                'issues': issue_serializer.data,
                'total_count': results['count'],
                'execution_time_ms': results.get('execution_time_ms'),
            })

        issue_serializer = IssueSerializer(queryset, many=True)
        return Response({
            'issues': issue_serializer.data,
            'total_count': results['count'],
            'execution_time_ms': results.get('execution_time_ms'),
        })


class SearchViewSet(viewsets.ViewSet):
    """
    ViewSet for search operations.

    Endpoints:
        POST /search/                    - Search issues
        POST /search/validate-jql/       - Validate JQL query
        POST /search/autocomplete/       - Get autocomplete suggestions
        GET  /search/history/            - Get search history
        GET  /search/stats/              - Get search statistics
    """

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def search_issues(self, request):
        """
        Search issues using JQL or filters.

        Request body can include:
        - jql: JQL query string
        - Additional filters (project, status, assignee, etc.)
        """
        user = request.user
        organization = getattr(user, 'current_organization', None)

        if not organization:
            return Response(
                {'error': 'Organization not found'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = SearchRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Extract search parameters
        jql = serializer.validated_data.get('jql')
        use_elasticsearch = serializer.validated_data.pop('use_elasticsearch', False)

        # Build filters dict
        filters = {
            k: v for k, v in serializer.validated_data.items()
            if k != 'jql' and v is not None
        }

        # Execute search
        search_service = SearchService(user=user, organization=organization)
        results = search_service.search_issues(
            query=jql,
            filters=filters if filters else None,
            use_elasticsearch=use_elasticsearch,
        )

        # Paginate results
        queryset = results['queryset']
        page = self.paginate_queryset(queryset)

        if page is not None:
            issue_serializer = IssueSerializer(page, many=True)
            return self.get_paginated_response({
                'issues': issue_serializer.data,
                'total_count': results['count'],
                'execution_time_ms': results.get('execution_time_ms'),
                'query': jql,
            })

        issue_serializer = IssueSerializer(queryset, many=True)
        return Response({
            'issues': issue_serializer.data,
            'total_count': results['count'],
            'execution_time_ms': results.get('execution_time_ms'),
            'query': jql,
        })

    def list(self, request):
        """Alias for search_issues (GET request)."""
        # Get query parameters and convert to POST-style data
        data = {}
        if request.query_params.get('jql'):
            data['jql'] = request.query_params.get('jql')
        if request.query_params.get('project'):
            data['project'] = request.query_params.get('project')
        if request.query_params.get('text'):
            data['text'] = request.query_params.get('text')

        # Update request data
        request._full_data = data
        return self.search_issues(request)

    @action(detail=False, methods=['post'])
    def validate_jql(self, request):
        """Validate JQL query syntax."""
        user = request.user
        organization = getattr(user, 'current_organization', None)

        serializer = JQLValidationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        search_service = SearchService(user=user, organization=organization)
        result = search_service.validate_jql(serializer.validated_data['jql'])

        response_serializer = JQLValidationResponseSerializer(result)
        return Response(response_serializer.data)

    @action(detail=False, methods=['post'])
    def autocomplete(self, request):
        """Get autocomplete suggestions for a field."""
        user = request.user
        organization = getattr(user, 'current_organization', None)

        serializer = AutocompleteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        search_service = SearchService(user=user, organization=organization)
        suggestions = search_service.get_autocomplete_suggestions(
            field=serializer.validated_data['field'],
            query=serializer.validated_data['query'],
            limit=serializer.validated_data.get('limit', 10),
        )

        response_serializer = AutocompleteResponseSerializer({
            'suggestions': suggestions
        })
        return Response(response_serializer.data)

    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get search history for current user."""
        user = request.user
        organization = getattr(user, 'current_organization', None)

        limit = int(request.query_params.get('limit', 20))

        history = SearchHistory.objects.for_user(user).for_organization(
            organization
        ).recent(limit=limit)

        serializer = SearchHistorySerializer(history, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get search statistics."""
        user = request.user
        organization = getattr(user, 'current_organization', None)

        # Get user's search history
        history = SearchHistory.objects.for_user(user).for_organization(organization)

        # Calculate stats
        total_searches = history.count()
        avg_time = history.aggregate(avg=Avg('execution_time_ms'))['avg'] or 0

        # Popular queries (top 10)
        popular = history.values('query').annotate(
            count=Count('id')
        ).order_by('-count')[:10]

        # Recent searches
        recent = history.recent(limit=10)

        stats = {
            'total_searches': total_searches,
            'avg_execution_time_ms': round(avg_time, 2),
            'popular_queries': list(popular),
            'recent_searches': recent,
        }

        serializer = SearchStatsSerializer(stats)
        return Response(serializer.data)
