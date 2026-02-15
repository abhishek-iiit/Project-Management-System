"""
Views for notifications.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q

from apps.notifications.models import Notification, NotificationPreference
from apps.notifications.serializers import (
    NotificationSerializer,
    NotificationPreferenceSerializer,
    NotificationPreferenceUpdateSerializer,
    NotificationStatsSerializer,
)
from apps.notifications.services import NotificationService


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for user notifications.

    Endpoints:
        GET    /notifications/               - List notifications
        GET    /notifications/{id}/          - Retrieve notification
        PUT    /notifications/{id}/read/     - Mark as read
        PUT    /notifications/{id}/unread/   - Mark as unread
        POST   /notifications/mark-all-read/ - Mark all as read
        GET    /notifications/stats/         - Get statistics
    """

    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        """Get queryset filtered by user."""
        user = self.request.user
        organization = getattr(user, 'current_organization', None)

        queryset = Notification.objects.for_user(user)

        if organization:
            queryset = queryset.for_organization(organization)

        # Filter by read status
        if self.request.query_params.get('unread') == 'true':
            queryset = queryset.unread()
        elif self.request.query_params.get('read') == 'true':
            queryset = queryset.read()

        # Filter by type
        notification_type = self.request.query_params.get('type')
        if notification_type:
            queryset = queryset.by_type(notification_type)

        return queryset.select_related(
            'organization',
            'recipient',
            'actor',
            'issue',
            'project',
            'sprint',
        )

    @action(detail=True, methods=['put'])
    def read(self, request, pk=None):
        """Mark notification as read."""
        notification = self.get_object()
        notification.mark_as_read()

        serializer = self.get_serializer(notification)
        return Response(serializer.data)

    @action(detail=True, methods=['put'])
    def unread(self, request, pk=None):
        """Mark notification as unread."""
        notification = self.get_object()
        notification.mark_as_unread()

        serializer = self.get_serializer(notification)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read."""
        user = request.user
        organization = getattr(user, 'current_organization', None)

        service = NotificationService(organization=organization)
        count = service.mark_all_as_read(user)

        return Response({
            'status': 'success',
            'message': f'{count} notifications marked as read'
        })

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get notification statistics."""
        user = request.user
        organization = getattr(user, 'current_organization', None)

        queryset = Notification.objects.for_user(user)
        if organization:
            queryset = queryset.for_organization(organization)

        total_count = queryset.count()
        unread_count = queryset.unread().count()
        read_count = queryset.read().count()

        # Group by type
        by_type = {}
        type_counts = queryset.values('notification_type').annotate(count=Count('id'))
        for item in type_counts:
            by_type[item['notification_type']] = item['count']

        stats = {
            'total_count': total_count,
            'unread_count': unread_count,
            'read_count': read_count,
            'by_type': by_type,
        }

        serializer = NotificationStatsSerializer(stats)
        return Response(serializer.data)


class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for notification preferences.

    Endpoints:
        GET    /notification-preferences/               - List preferences
        POST   /notification-preferences/               - Create preference
        GET    /notification-preferences/{id}/          - Retrieve preference
        PUT    /notification-preferences/{id}/          - Update preference
        DELETE /notification-preferences/{id}/          - Delete preference
        GET    /notification-preferences/current/       - Get current user's preferences
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get queryset filtered by user."""
        user = self.request.user
        organization = getattr(user, 'current_organization', None)

        queryset = NotificationPreference.objects.for_user(user)

        if organization:
            queryset = queryset.for_organization(organization)

        return queryset.select_related(
            'organization',
            'user',
            'project',
        )

    def get_serializer_class(self):
        """Get appropriate serializer class."""
        if self.action in ['update', 'partial_update']:
            return NotificationPreferenceUpdateSerializer
        return NotificationPreferenceSerializer

    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current user's global preferences."""
        user = request.user
        organization = getattr(user, 'current_organization', None)

        if not organization:
            return Response(
                {'error': 'No organization selected'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get or create global preferences
        preference = NotificationPreference.get_or_create_for_user(
            user=user,
            organization=organization,
            project=None,
        )

        serializer = NotificationPreferenceSerializer(preference)
        return Response(serializer.data)
