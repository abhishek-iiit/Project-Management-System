"""
Audit service for creating and managing audit logs.
"""

import time
import logging
from typing import Dict, Any, Optional
from django.contrib.auth import get_user_model

from apps.audit.models import AuditLog, AuditAction
from apps.audit.utils import ChangeTracker

User = get_user_model()
logger = logging.getLogger(__name__)


class AuditService:
    """Service for creating and managing audit logs."""

    @staticmethod
    def log_create(
        entity_type: str,
        entity,
        user=None,
        organization=None,
        request=None,
        metadata: Optional[Dict] = None,
    ):
        """
        Log entity creation.

        Args:
            entity_type: Type of entity (e.g., 'Issue', 'Project')
            entity: Created entity instance
            user: User who created it
            organization: Organization context
            request: HTTP request object
            metadata: Additional metadata
        """
        changes = ChangeTracker.get_model_changes(entity, old_instance=None)

        return AuditLog.log_action(
            action=AuditAction.CREATE,
            entity_type=entity_type,
            entity_id=entity.pk,
            entity_name=str(entity),
            changes=changes,
            user=user,
            organization=organization,
            metadata=metadata,
            **AuditService._extract_request_info(request)
        )

    @staticmethod
    def log_update(
        entity_type: str,
        entity,
        old_entity,
        user=None,
        organization=None,
        request=None,
        metadata: Optional[Dict] = None,
    ):
        """
        Log entity update.

        Args:
            entity_type: Type of entity
            entity: Updated entity instance
            old_entity: Previous entity state
            user: User who updated it
            organization: Organization context
            request: HTTP request object
            metadata: Additional metadata
        """
        changes = ChangeTracker.get_model_changes(entity, old_entity)

        # Only log if there are actual changes
        if not changes:
            return None

        return AuditLog.log_action(
            action=AuditAction.UPDATE,
            entity_type=entity_type,
            entity_id=entity.pk,
            entity_name=str(entity),
            changes=changes,
            user=user,
            organization=organization,
            metadata=metadata,
            **AuditService._extract_request_info(request)
        )

    @staticmethod
    def log_delete(
        entity_type: str,
        entity_id,
        entity_name: str,
        user=None,
        organization=None,
        request=None,
        metadata: Optional[Dict] = None,
    ):
        """
        Log entity deletion.

        Args:
            entity_type: Type of entity
            entity_id: ID of deleted entity
            entity_name: Name of deleted entity
            user: User who deleted it
            organization: Organization context
            request: HTTP request object
            metadata: Additional metadata
        """
        return AuditLog.log_action(
            action=AuditAction.DELETE,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            user=user,
            organization=organization,
            metadata=metadata,
            **AuditService._extract_request_info(request)
        )

    @staticmethod
    def log_transition(
        issue,
        from_status,
        to_status,
        user=None,
        organization=None,
        request=None,
    ):
        """
        Log issue status transition.

        Args:
            issue: Issue instance
            from_status: Previous status
            to_status: New status
            user: User who transitioned
            organization: Organization context
            request: HTTP request object
        """
        changes = {
            'status': {
                'from': str(from_status.id),
                'to': str(to_status.id),
                'from_name': from_status.name,
                'to_name': to_status.name,
            }
        }

        metadata = {
            'transition': {
                'from_category': from_status.category,
                'to_category': to_status.category,
            }
        }

        return AuditLog.log_action(
            action=AuditAction.TRANSITION,
            entity_type='Issue',
            entity_id=issue.pk,
            entity_name=issue.key,
            changes=changes,
            user=user,
            organization=organization,
            metadata=metadata,
            **AuditService._extract_request_info(request)
        )

    @staticmethod
    def log_comment(
        issue,
        comment,
        user=None,
        organization=None,
        request=None,
    ):
        """
        Log comment creation.

        Args:
            issue: Issue instance
            comment: Comment instance
            user: User who commented
            organization: Organization context
            request: HTTP request object
        """
        metadata = {
            'comment_id': str(comment.pk),
            'comment_body': comment.body[:500],  # First 500 chars
        }

        return AuditLog.log_action(
            action=AuditAction.COMMENT,
            entity_type='Issue',
            entity_id=issue.pk,
            entity_name=issue.key,
            user=user,
            organization=organization,
            metadata=metadata,
            **AuditService._extract_request_info(request)
        )

    @staticmethod
    def log_assign(
        issue,
        from_assignee,
        to_assignee,
        user=None,
        organization=None,
        request=None,
    ):
        """
        Log issue assignment.

        Args:
            issue: Issue instance
            from_assignee: Previous assignee
            to_assignee: New assignee
            user: User who assigned
            organization: Organization context
            request: HTTP request object
        """
        changes = {
            'assignee': {
                'from': str(from_assignee.id) if from_assignee else None,
                'to': str(to_assignee.id) if to_assignee else None,
                'from_name': from_assignee.email if from_assignee else 'Unassigned',
                'to_name': to_assignee.email if to_assignee else 'Unassigned',
            }
        }

        return AuditLog.log_action(
            action=AuditAction.ASSIGN,
            entity_type='Issue',
            entity_id=issue.pk,
            entity_name=issue.key,
            changes=changes,
            user=user,
            organization=organization,
            **AuditService._extract_request_info(request)
        )

    @staticmethod
    def log_login(user, success=True, error_message='', request=None):
        """
        Log user login attempt.

        Args:
            user: User who logged in
            success: Whether login succeeded
            error_message: Error message if failed
            request: HTTP request object
        """
        return AuditLog.log_action(
            action=AuditAction.LOGIN if success else AuditAction.LOGIN_FAILED,
            entity_type='User',
            entity_id=user.pk if user else None,
            entity_name=user.email if user else 'Unknown',
            user=user if success else None,
            success=success,
            error_message=error_message,
            **AuditService._extract_request_info(request)
        )

    @staticmethod
    def log_export(
        entity_type: str,
        count: int,
        format: str,
        user=None,
        organization=None,
        request=None,
    ):
        """
        Log data export.

        Args:
            entity_type: Type of entity exported
            count: Number of entities exported
            format: Export format (csv, json, etc.)
            user: User who exported
            organization: Organization context
            request: HTTP request object
        """
        metadata = {
            'count': count,
            'format': format,
        }

        return AuditLog.log_action(
            action=AuditAction.EXPORT,
            entity_type=entity_type,
            entity_name=f"{count} {entity_type}(s)",
            user=user,
            organization=organization,
            metadata=metadata,
            **AuditService._extract_request_info(request)
        )

    @staticmethod
    def _extract_request_info(request) -> Dict[str, Any]:
        """
        Extract information from HTTP request.

        Args:
            request: HTTP request object

        Returns:
            Dict with IP, user agent, method, and path
        """
        if not request:
            return {}

        # Get IP address
        ip_address = AuditService._get_client_ip(request)

        # Get user agent
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        return {
            'ip_address': ip_address,
            'user_agent': user_agent[:500],  # Limit length
            'request_method': request.method,
            'request_path': request.path,
        }

    @staticmethod
    def _get_client_ip(request) -> Optional[str]:
        """
        Get client IP address from request.

        Args:
            request: HTTP request object

        Returns:
            IP address string or None
        """
        # Check for X-Forwarded-For header (proxy/load balancer)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()

        # Fall back to REMOTE_ADDR
        return request.META.get('REMOTE_ADDR')

    @staticmethod
    def get_entity_history(entity_type: str, entity_id: str, limit: int = 50):
        """
        Get audit history for a specific entity.

        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            limit: Maximum number of logs to return

        Returns:
            QuerySet of AuditLog objects
        """
        return AuditLog.objects.for_entity(
            entity_type, entity_id
        ).order_by('-created_at')[:limit]

    @staticmethod
    def cleanup_old_logs(days: int = 90):
        """
        Delete audit logs older than specified days.

        Args:
            days: Number of days to retain

        Returns:
            Number of deleted logs
        """
        from django.utils import timezone
        from datetime import timedelta

        cutoff_date = timezone.now() - timedelta(days=days)

        count = AuditLog.objects.filter(
            created_at__lt=cutoff_date
        ).delete()[0]

        logger.info(f"Deleted {count} audit logs older than {days} days")
        return count
