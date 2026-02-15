"""
Rate limiting middleware using Redis.
"""

import hashlib
from django.core.cache import cache
from django.http import JsonResponse
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
import time


class RateLimitMiddleware(MiddlewareMixin):
    """
    Rate limiting middleware.

    Limits requests per IP address and per user.
    Uses sliding window algorithm with Redis.
    """

    # Rate limits (requests per time window)
    LIMITS = {
        'anonymous': {
            'requests': 100,  # 100 requests
            'window': 3600,  # per hour
        },
        'authenticated': {
            'requests': 1000,  # 1000 requests
            'window': 3600,  # per hour
        },
        'auth_endpoints': {
            'requests': 10,  # 10 requests
            'window': 600,  # per 10 minutes
        },
        'api_endpoints': {
            'requests': 100,  # 100 requests
            'window': 60,  # per minute
        },
    }

    def process_request(self, request):
        """
        Check rate limits for incoming request.

        Args:
            request: Django request object

        Returns:
            None if within limits, 429 response if rate limit exceeded
        """
        # Skip rate limiting in development if configured
        if settings.DEBUG and not getattr(settings, 'RATE_LIMIT_IN_DEBUG', False):
            return None

        # Determine rate limit type
        if request.path.startswith('/api/v1/auth/'):
            limit_type = 'auth_endpoints'
        elif request.path.startswith('/api/'):
            limit_type = 'api_endpoints'
        elif request.user.is_authenticated:
            limit_type = 'authenticated'
        else:
            limit_type = 'anonymous'

        # Get limit configuration
        limit_config = self.LIMITS[limit_type]
        max_requests = limit_config['requests']
        window_seconds = limit_config['window']

        # Generate cache key
        cache_key = self._get_cache_key(request, limit_type)

        # Check rate limit
        current_count = self._increment_counter(cache_key, window_seconds)

        # Add rate limit headers to response
        remaining = max(0, max_requests - current_count)
        reset_time = int(time.time()) + window_seconds

        # Store for adding to response later
        request._rate_limit_headers = {
            'X-RateLimit-Limit': str(max_requests),
            'X-RateLimit-Remaining': str(remaining),
            'X-RateLimit-Reset': str(reset_time),
        }

        # Check if limit exceeded
        if current_count > max_requests:
            return JsonResponse(
                {
                    'error': {
                        'code': 'RATE_LIMIT_EXCEEDED',
                        'message': 'Rate limit exceeded. Please try again later.',
                        'details': {
                            'limit': max_requests,
                            'window_seconds': window_seconds,
                            'reset_at': reset_time,
                        }
                    }
                },
                status=429,
                headers=request._rate_limit_headers
            )

        return None

    def process_response(self, request, response):
        """
        Add rate limit headers to response.

        Args:
            request: Django request object
            response: Django response object

        Returns:
            Response with rate limit headers
        """
        # Add rate limit headers if available
        if hasattr(request, '_rate_limit_headers'):
            for header, value in request._rate_limit_headers.items():
                response[header] = value

        return response

    def _get_cache_key(self, request, limit_type: str) -> str:
        """
        Generate cache key for rate limiting.

        Args:
            request: Django request object
            limit_type: Type of rate limit

        Returns:
            Cache key string
        """
        # Use user ID if authenticated, otherwise IP address
        if request.user.is_authenticated:
            identifier = f"user:{request.user.id}"
        else:
            # Get client IP address
            ip_address = self._get_client_ip(request)
            identifier = f"ip:{ip_address}"

        # Create cache key
        cache_key = f"rate_limit:{limit_type}:{identifier}"

        return cache_key

    def _get_client_ip(self, request) -> str:
        """
        Get client IP address from request.

        Args:
            request: Django request object

        Returns:
            IP address string
        """
        # Check X-Forwarded-For header (for proxied requests)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Take the first IP in the chain
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            # Use REMOTE_ADDR
            ip = request.META.get('REMOTE_ADDR', '0.0.0.0')

        return ip

    def _increment_counter(self, cache_key: str, window_seconds: int) -> int:
        """
        Increment request counter using sliding window.

        Args:
            cache_key: Redis cache key
            window_seconds: Time window in seconds

        Returns:
            Current request count
        """
        current_time = time.time()
        window_start = current_time - window_seconds

        # Use Redis sorted set for sliding window
        # Note: This is a simplified version. In production, use Redis directly
        # with ZREMRANGEBYSCORE and ZADD commands for better performance

        # Get or create counter
        counter = cache.get(cache_key, [])

        # Remove old entries outside the window
        counter = [timestamp for timestamp in counter if timestamp > window_start]

        # Add current request
        counter.append(current_time)

        # Store updated counter
        cache.set(cache_key, counter, window_seconds)

        return len(counter)


class IPWhitelistMiddleware(MiddlewareMixin):
    """
    Whitelist specific IP addresses for admin access.

    Configure ADMIN_IP_WHITELIST in settings.
    """

    def process_request(self, request):
        """
        Check if request to admin is from whitelisted IP.

        Args:
            request: Django request object

        Returns:
            None if allowed, 403 response if forbidden
        """
        # Only check admin paths
        if not request.path.startswith('/admin/'):
            return None

        # Get IP whitelist from settings
        whitelist = getattr(settings, 'ADMIN_IP_WHITELIST', None)

        # If no whitelist configured, allow all
        if not whitelist:
            return None

        # Get client IP
        client_ip = self._get_client_ip(request)

        # Check if IP is whitelisted
        if client_ip not in whitelist:
            return JsonResponse(
                {
                    'error': {
                        'code': 'FORBIDDEN',
                        'message': 'Access denied. Your IP address is not whitelisted.',
                    }
                },
                status=403
            )

        return None

    def _get_client_ip(self, request) -> str:
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        return ip
