"""
API-related middleware for versioning and headers.
"""

from django.utils.deprecation import MiddlewareMixin
from datetime import datetime, timedelta


class APIVersionMiddleware(MiddlewareMixin):
    """
    Middleware for handling API versioning and deprecation headers.
    """

    # Deprecation schedule (version: sunset_date)
    DEPRECATED_VERSIONS = {
        # Example: 'v0': '2026-06-01',
    }

    def process_response(self, request, response):
        """Add API version headers to response."""
        # Only process API requests
        if not request.path.startswith('/api/'):
            return response

        # Extract API version from path
        path_parts = request.path.split('/')
        version = None
        if len(path_parts) >= 3 and path_parts[2].startswith('v'):
            version = path_parts[2]

        # Add version header
        if version:
            response['X-API-Version'] = version

        # Add deprecation headers if applicable
        if version in self.DEPRECATED_VERSIONS:
            sunset_date = self.DEPRECATED_VERSIONS[version]
            response['Deprecation'] = 'true'
            response['Sunset'] = sunset_date
            response['Link'] = '</api/v1/>; rel="successor-version"'
            response['Warning'] = (
                f'299 - "API version {version} is deprecated and will be '
                f'sunset on {sunset_date}. Please migrate to v1."'
            )

        return response


class APIHeadersMiddleware(MiddlewareMixin):
    """
    Middleware for adding standard API headers.
    """

    def process_response(self, request, response):
        """Add standard headers to API responses."""
        # Only process API requests
        if not request.path.startswith('/api/'):
            return response

        # Add request ID if available
        request_id = getattr(request, 'id', None)
        if request_id:
            response['X-Request-ID'] = request_id

        # Add server time
        response['X-Server-Time'] = datetime.utcnow().isoformat() + 'Z'

        # Add API information
        response['X-API-Name'] = 'BugsTracker API'
        response['X-Powered-By'] = 'Django/DRF'

        return response


class RequestIDMiddleware(MiddlewareMixin):
    """
    Middleware for generating unique request IDs for tracking.
    """

    def process_request(self, request):
        """Generate unique request ID."""
        import uuid
        request.id = str(uuid.uuid4())

    def process_response(self, request, response):
        """Add request ID to response."""
        request_id = getattr(request, 'id', None)
        if request_id:
            response['X-Request-ID'] = request_id
        return response


class CORSHeadersMiddleware(MiddlewareMixin):
    """
    Additional CORS headers for API responses.
    (Supplements django-cors-headers)
    """

    def process_response(self, request, response):
        """Add additional CORS headers."""
        # Only process API requests
        if not request.path.startswith('/api/'):
            return response

        # Expose custom headers to clients
        response['Access-Control-Expose-Headers'] = ', '.join([
            'X-API-Version',
            'X-Request-ID',
            'X-RateLimit-Limit',
            'X-RateLimit-Remaining',
            'X-RateLimit-Reset',
            'X-Server-Time',
            'Deprecation',
            'Sunset',
        ])

        return response


class HealthCheckMiddleware(MiddlewareMixin):
    """
    Middleware for handling health check requests.
    Bypasses authentication and rate limiting for health checks.
    """

    HEALTH_CHECK_PATHS = [
        '/health/',
        '/api/health/',
        '/healthz/',
        '/ping/',
    ]

    def process_request(self, request):
        """Handle health check requests."""
        if request.path in self.HEALTH_CHECK_PATHS:
            from django.http import JsonResponse
            from django.db import connection

            health_status = {
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'version': '1.0.0',
                'checks': {}
            }

            # Check database connection
            try:
                connection.ensure_connection()
                health_status['checks']['database'] = 'ok'
            except Exception as e:
                health_status['checks']['database'] = 'error'
                health_status['status'] = 'unhealthy'

            # Check cache
            try:
                from django.core.cache import cache
                cache.set('health_check', 'ok', 10)
                if cache.get('health_check') == 'ok':
                    health_status['checks']['cache'] = 'ok'
                else:
                    health_status['checks']['cache'] = 'error'
                    health_status['status'] = 'degraded'
            except Exception as e:
                health_status['checks']['cache'] = 'error'
                health_status['status'] = 'degraded'

            # Return response
            status_code = 200 if health_status['status'] == 'healthy' else 503
            return JsonResponse(health_status, status=status_code)

        return None


class MaintenanceModeMiddleware(MiddlewareMixin):
    """
    Middleware for handling maintenance mode.
    Set MAINTENANCE_MODE = True in settings to enable.
    """

    def process_request(self, request):
        """Check if system is in maintenance mode."""
        from django.conf import settings
        from django.http import JsonResponse

        # Skip health checks and admin
        if (
            request.path in HealthCheckMiddleware.HEALTH_CHECK_PATHS or
            request.path.startswith('/admin/')
        ):
            return None

        # Check maintenance mode
        if getattr(settings, 'MAINTENANCE_MODE', False):
            # Allow superusers through
            if request.user and request.user.is_authenticated and request.user.is_superuser:
                return None

            # Return maintenance response
            return JsonResponse(
                {
                    'status': 'error',
                    'error': {
                        'code': 'MAINTENANCE_MODE',
                        'message': 'System is currently under maintenance. Please try again later.',
                        'retry_after': getattr(settings, 'MAINTENANCE_RETRY_AFTER', 3600),
                    }
                },
                status=503
            )

        return None
