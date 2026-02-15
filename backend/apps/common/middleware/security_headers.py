"""
Security headers middleware.

Adds comprehensive security headers to all HTTP responses.
"""

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Add security headers to all responses.

    Headers added:
    - X-Content-Type-Options
    - X-Frame-Options
    - X-XSS-Protection
    - Strict-Transport-Security (HSTS)
    - Content-Security-Policy (CSP)
    - Referrer-Policy
    - Permissions-Policy
    """

    def process_response(self, request, response):
        """
        Add security headers to response.

        Args:
            request: Django request object
            response: Django response object

        Returns:
            Response with security headers added
        """
        # X-Content-Type-Options: Prevent MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'

        # X-Frame-Options: Prevent clickjacking
        response['X-Frame-Options'] = 'DENY'

        # X-XSS-Protection: Enable XSS filter (legacy, but still useful)
        response['X-XSS-Protection'] = '1; mode=block'

        # Strict-Transport-Security (HSTS): Force HTTPS
        if settings.SECURE_SSL_REDIRECT:
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'

        # Content-Security-Policy (CSP): Restrict resource loading
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # Allow inline scripts (adjust as needed)
            "style-src 'self' 'unsafe-inline'",  # Allow inline styles
            "img-src 'self' data: https:",  # Allow images from self, data URLs, and HTTPS
            "font-src 'self' data:",
            "connect-src 'self'",
            "frame-ancestors 'none'",  # Prevent framing (similar to X-Frame-Options)
            "base-uri 'self'",
            "form-action 'self'",
            "upgrade-insecure-requests",  # Upgrade HTTP to HTTPS
        ]
        response['Content-Security-Policy'] = '; '.join(csp_directives)

        # Referrer-Policy: Control referrer information
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Permissions-Policy: Control browser features
        permissions_directives = [
            'geolocation=()',  # Disable geolocation
            'microphone=()',  # Disable microphone
            'camera=()',  # Disable camera
            'payment=()',  # Disable payment API
            'usb=()',  # Disable USB
            'magnetometer=()',  # Disable magnetometer
            'gyroscope=()',  # Disable gyroscope
            'accelerometer=()',  # Disable accelerometer
        ]
        response['Permissions-Policy'] = ', '.join(permissions_directives)

        # Cache-Control for sensitive endpoints
        if request.path.startswith('/api/v1/auth/') or request.path.startswith('/admin/'):
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
            response['Pragma'] = 'no-cache'

        return response


class SecureRequestMiddleware(MiddlewareMixin):
    """
    Additional security checks on incoming requests.
    """

    # Maximum request body size (100 MB)
    MAX_BODY_SIZE = 100 * 1024 * 1024

    def process_request(self, request):
        """
        Perform security checks on incoming request.

        Args:
            request: Django request object

        Returns:
            None if request is valid, HttpResponse if request should be rejected
        """
        # Check request body size
        if request.META.get('CONTENT_LENGTH'):
            content_length = int(request.META['CONTENT_LENGTH'])
            if content_length > self.MAX_BODY_SIZE:
                from django.http import HttpResponse
                return HttpResponse(
                    'Request body too large',
                    status=413,
                    content_type='text/plain'
                )

        # Check for null bytes in path (directory traversal attempt)
        if '\x00' in request.path:
            from django.http import HttpResponseBadRequest
            return HttpResponseBadRequest('Invalid request path')

        return None
