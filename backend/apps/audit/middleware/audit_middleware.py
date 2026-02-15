"""
Middleware for automatic audit logging of requests.
"""

import time
import logging
from django.utils.deprecation import MiddlewareMixin

from apps.audit.services import AuditService

logger = logging.getLogger(__name__)


class AuditMiddleware(MiddlewareMixin):
    """
    Middleware for automatic audit logging.

    Logs all authenticated requests to the system.
    """

    # Paths to exclude from audit logging
    EXCLUDED_PATHS = [
        '/admin/jsi18n/',
        '/static/',
        '/media/',
        '/__debug__/',
        '/api/v1/auth/refresh/',  # Don't log token refreshes
    ]

    # Methods to exclude
    EXCLUDED_METHODS = ['OPTIONS', 'HEAD']

    def process_request(self, request):
        """Store start time for duration tracking."""
        request._audit_start_time = time.time()
        return None

    def process_response(self, request, response):
        """Log request after response is generated."""
        # Skip if excluded
        if self._should_skip(request):
            return response

        # Only log for authenticated users
        if not request.user or not request.user.is_authenticated:
            return response

        # Calculate duration
        duration_ms = None
        if hasattr(request, '_audit_start_time'):
            duration_ms = int((time.time() - request._audit_start_time) * 1000)

        # Determine success based on status code
        success = 200 <= response.status_code < 400

        # Log based on request method
        try:
            if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
                self._log_mutating_request(request, response, success, duration_ms)

        except Exception as e:
            # Don't fail the request if audit logging fails
            logger.error(f"Failed to create audit log: {str(e)}", exc_info=True)

        return response

    def _should_skip(self, request):
        """Check if request should be skipped."""
        # Check excluded paths
        for excluded_path in self.EXCLUDED_PATHS:
            if request.path.startswith(excluded_path):
                return True

        # Check excluded methods
        if request.method in self.EXCLUDED_METHODS:
            return True

        return False

    def _log_mutating_request(self, request, response, success, duration_ms):
        """
        Log mutating requests (POST, PUT, PATCH, DELETE).

        Args:
            request: HTTP request
            response: HTTP response
            success: Whether request succeeded
            duration_ms: Request duration in milliseconds
        """
        # Don't log here - this is handled by views/signals
        # This middleware is mainly for future extensions
        pass
