"""
Multi-tenancy middleware for organization-based isolation.

This middleware:
1. Extracts organization ID from request headers
2. Validates user belongs to the organization
3. Sets current organization context on the user
4. Ensures data isolation between organizations
"""

import logging
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied

logger = logging.getLogger(__name__)


class TenantMiddleware(MiddlewareMixin):
    """
    Middleware to handle multi-tenancy (organization-based).

    Expects 'X-Organization-ID' header in requests.
    Sets request.organization and user.current_organization.

    Security:
    - Validates user belongs to the organization
    - Prevents cross-organization data access
    - Logs all organization switches for audit
    """

    TENANT_HEADER = 'HTTP_X_ORGANIZATION_ID'
    PUBLIC_PATHS = [
        '/api/v1/auth/login/',
        '/api/v1/auth/register/',
        '/api/v1/auth/refresh/',
        '/api/v1/organizations/',  # To list user's organizations
        '/admin/',
        '/api/schema/',
        '/api/docs/',
    ]

    def process_request(self, request):
        """
        Process incoming request to extract and validate organization context.

        Args:
            request: Django HTTP request

        Returns:
            None or JsonResponse (if validation fails)
        """
        # Skip tenant validation for public paths
        if self._is_public_path(request.path):
            request.organization = None
            return None

        # Skip for unauthenticated requests (handled by DRF permissions)
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            request.organization = None
            return None

        # Extract organization ID from header
        organization_id = request.META.get(self.TENANT_HEADER)

        if not organization_id:
            logger.warning(
                f"Missing organization header for user {request.user.id} on path {request.path}"
            )
            return JsonResponse(
                {
                    'status': 'error',
                    'error': {
                        'code': 'ORGANIZATION_REQUIRED',
                        'message': 'X-Organization-ID header is required',
                    }
                },
                status=400
            )

        # Validate organization exists and user belongs to it
        try:
            organization = self._get_organization(request.user, organization_id)
            request.organization = organization
            request.user.current_organization = organization

            logger.debug(
                f"User {request.user.id} accessing organization {organization.id}"
            )

        except PermissionDenied as e:
            logger.warning(
                f"User {request.user.id} denied access to organization {organization_id}: {str(e)}"
            )
            return JsonResponse(
                {
                    'status': 'error',
                    'error': {
                        'code': 'ORGANIZATION_ACCESS_DENIED',
                        'message': str(e),
                    }
                },
                status=403
            )
        except Exception as e:
            logger.error(
                f"Error validating organization {organization_id} for user {request.user.id}: {str(e)}"
            )
            return JsonResponse(
                {
                    'status': 'error',
                    'error': {
                        'code': 'ORGANIZATION_VALIDATION_ERROR',
                        'message': 'Failed to validate organization access',
                    }
                },
                status=500
            )

        return None

    def _is_public_path(self, path: str) -> bool:
        """
        Check if path is public (doesn't require organization context).

        Args:
            path: Request path

        Returns:
            True if path is public
        """
        return any(path.startswith(public_path) for public_path in self.PUBLIC_PATHS)

    def _get_organization(self, user, organization_id):
        """
        Get and validate organization for user.

        Args:
            user: Authenticated user
            organization_id: Organization UUID

        Returns:
            Organization instance

        Raises:
            PermissionDenied: If user doesn't belong to organization
        """
        # Import here to avoid circular imports
        from apps.organizations.models import Organization, OrganizationMember

        # Validate UUID format
        try:
            import uuid
            uuid.UUID(organization_id)
        except ValueError:
            raise PermissionDenied("Invalid organization ID format")

        # Check if user is member of organization
        try:
            membership = OrganizationMember.objects.select_related('organization').get(
                user=user,
                organization_id=organization_id,
                is_active=True
            )
            return membership.organization

        except OrganizationMember.DoesNotExist:
            raise PermissionDenied(
                f"User does not have access to organization {organization_id}"
            )

    def process_response(self, request, response):
        """
        Process outgoing response.

        Can be used to add organization-related headers to response.
        """
        # Add organization ID to response headers (for debugging)
        if hasattr(request, 'organization') and request.organization:
            response['X-Organization-ID'] = str(request.organization.id)

        return response
