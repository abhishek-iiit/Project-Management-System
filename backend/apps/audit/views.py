"""
Views for audit logs.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q

from apps.audit.models import AuditLog
from apps.audit.serializers import (
    AuditLogSerializer,
    AuditLogListSerializer,
    AuditStatsSerializer,
)
from apps.audit.services import AuditService


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for audit logs (read-only).

    Endpoints:
        GET /audit-logs/              - List audit logs
        GET /audit-logs/{id}/         - Retrieve audit log
        GET /audit-logs/entity/{type}/{id}/ - Get entity history
        GET /audit-logs/stats/        - Get audit statistics
        POST /audit-logs/export/      - Export audit logs
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get queryset filtered by organization."""
        user = self.request.user
        organization = getattr(user, 'current_organization', None)

        if not organization:
            return AuditLog.objects.none()

        queryset = AuditLog.objects.for_organization(organization)

        # Filter by user
        user_id = self.request.query_params.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        # Filter by action
        action = self.request.query_params.get('action')
        if action:
            queryset = queryset.by_action(action)

        # Filter by entity type
        entity_type = self.request.query_params.get('entity_type')
        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)

        # Filter by entity ID
        entity_id = self.request.query_params.get('entity_id')
        if entity_id:
            queryset = queryset.filter(entity_id=entity_id)

        # Filter by success
        success = self.request.query_params.get('success')
        if success == 'true':
            queryset = queryset.successful()
        elif success == 'false':
            queryset = queryset.failed()

        # Filter by date range
        date_from = self.request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)

        date_to = self.request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)

        return queryset.select_related(
            'organization',
            'user',
        ).order_by('-created_at')

    def get_serializer_class(self):
        """Get appropriate serializer class."""
        if self.action == 'list':
            return AuditLogListSerializer
        return AuditLogSerializer

    @action(detail=False, methods=['get'], url_path='entity/(?P<entity_type>[^/.]+)/(?P<entity_id>[^/.]+)')
    def entity_history(self, request, entity_type=None, entity_id=None):
        """Get audit history for a specific entity."""
        limit = int(request.query_params.get('limit', 50))

        logs = AuditService.get_entity_history(
            entity_type=entity_type,
            entity_id=entity_id,
            limit=limit
        )

        # Filter by organization
        organization = getattr(request.user, 'current_organization', None)
        if organization:
            logs = logs.filter(organization=organization)

        serializer = AuditLogSerializer(logs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get audit statistics."""
        user = request.user
        organization = getattr(user, 'current_organization', None)

        if not organization:
            return Response(
                {'error': 'No organization selected'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get logs for organization
        logs = AuditLog.objects.for_organization(organization)

        # Filter by date range if provided
        days = int(request.query_params.get('days', 30))
        logs = logs.recent(days=days)

        # Calculate stats
        total_logs = logs.count()
        successful_logs = logs.successful().count()
        failed_logs = logs.failed().count()

        # Group by action
        by_action = {}
        for item in logs.values('action').annotate(count=Count('id')):
            by_action[item['action']] = item['count']

        # Group by entity type
        by_entity_type = {}
        for item in logs.values('entity_type').annotate(count=Count('id')):
            by_entity_type[item['entity_type']] = item['count']

        # Top users
        by_user = list(
            logs.values('user__email')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        # Recent activity
        recent_activity = logs.order_by('-created_at')[:20]

        stats = {
            'total_logs': total_logs,
            'successful_logs': successful_logs,
            'failed_logs': failed_logs,
            'by_action': by_action,
            'by_entity_type': by_entity_type,
            'by_user': by_user,
            'recent_activity': recent_activity,
        }

        serializer = AuditStatsSerializer(stats)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def export(self, request):
        """Export audit logs to CSV."""
        import csv
        from django.http import HttpResponse

        user = request.user
        organization = getattr(user, 'current_organization', None)

        if not organization:
            return Response(
                {'error': 'No organization selected'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get filtered logs
        queryset = self.get_queryset()

        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="audit_logs.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Timestamp',
            'User',
            'Action',
            'Entity Type',
            'Entity Name',
            'Changes',
            'IP Address',
            'Success',
        ])

        for log in queryset[:1000]:  # Limit to 1000 rows
            writer.writerow([
                log.created_at.isoformat(),
                log.user.email if log.user else 'System',
                log.action,
                log.entity_type,
                log.entity_name,
                log.get_change_summary(),
                log.ip_address or '',
                'Yes' if log.success else 'No',
            ])

        # Log export action
        AuditService.log_export(
            entity_type='AuditLog',
            count=min(queryset.count(), 1000),
            format='csv',
            user=user,
            organization=organization,
            request=request,
        )

        return response
