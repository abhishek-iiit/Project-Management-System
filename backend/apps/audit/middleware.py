"""
Audit middleware for tracking changes.
"""

from django.utils.deprecation import MiddlewareMixin


class AuditMiddleware(MiddlewareMixin):
    """
    Middleware to track user actions for audit logging.

    Will be implemented in Phase 12.
    """

    def process_request(self, request):
        """Process incoming request."""
        # TODO: Implement in Phase 12
        return None

    def process_response(self, request, response):
        """Process outgoing response."""
        # TODO: Implement in Phase 12
        return response
