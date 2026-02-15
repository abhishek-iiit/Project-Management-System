"""
Rate limiting utilities and decorators.
"""

from functools import wraps
from django.core.cache import cache
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta
import time


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, message="Rate limit exceeded", retry_after=None):
        self.message = message
        self.retry_after = retry_after
        super().__init__(self.message)


class RateLimiter:
    """
    Rate limiter using Redis cache.
    Implements sliding window rate limiting.
    """

    @staticmethod
    def get_identifier(request):
        """
        Get unique identifier for rate limiting.
        Uses user ID for authenticated requests, IP for anonymous.
        """
        if request.user and request.user.is_authenticated:
            return f"user:{request.user.id}"

        # Get IP address (handle proxies)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')

        return f"ip:{ip}"

    @staticmethod
    def check_rate_limit(identifier, limit, period, scope='default'):
        """
        Check if request exceeds rate limit.

        Args:
            identifier: Unique identifier (user ID or IP)
            limit: Maximum number of requests
            period: Time period in seconds
            scope: Rate limit scope (default, burst, etc.)

        Returns:
            tuple: (allowed: bool, retry_after: int)
        """
        cache_key = f"ratelimit:{scope}:{identifier}"

        # Get current window data
        now = time.time()
        window_start = now - period

        # Get existing requests in current window
        requests = cache.get(cache_key, [])

        # Filter requests within current window
        requests = [req_time for req_time in requests if req_time > window_start]

        # Check if limit exceeded
        if len(requests) >= limit:
            # Calculate retry_after (time until oldest request expires)
            oldest_request = min(requests)
            retry_after = int(oldest_request + period - now)
            return False, retry_after

        # Add current request
        requests.append(now)

        # Save to cache with expiry
        cache.set(cache_key, requests, timeout=period)

        return True, 0

    @staticmethod
    def get_rate_limit_headers(identifier, limit, period, scope='default'):
        """
        Get rate limit headers for response.

        Returns:
            dict: Headers with rate limit info
        """
        cache_key = f"ratelimit:{scope}:{identifier}"

        now = time.time()
        window_start = now - period

        requests = cache.get(cache_key, [])
        requests = [req_time for req_time in requests if req_time > window_start]

        remaining = max(0, limit - len(requests))

        # Calculate reset time
        if requests:
            oldest_request = min(requests)
            reset_time = int(oldest_request + period)
        else:
            reset_time = int(now + period)

        return {
            'X-RateLimit-Limit': str(limit),
            'X-RateLimit-Remaining': str(remaining),
            'X-RateLimit-Reset': str(reset_time),
        }


def ratelimit(scope='default', limit=None, period=None):
    """
    Decorator for rate limiting view functions.

    Usage:
        @ratelimit(scope='api', limit=100, period=3600)
        def my_view(request):
            ...

    Args:
        scope: Rate limit scope identifier
        limit: Maximum requests (defaults from settings)
        period: Time period in seconds (defaults from settings)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            # Get defaults from settings if not provided
            if limit is None or period is None:
                user_limit = 1000
                user_period = 3600
                anon_limit = 100
                anon_period = 3600
            else:
                user_limit = anon_limit = limit
                user_period = anon_period = period

            # Determine limit based on authentication
            if request.user and request.user.is_authenticated:
                req_limit = user_limit
                req_period = user_period
            else:
                req_limit = anon_limit
                req_period = anon_period

            # Check rate limit
            identifier = RateLimiter.get_identifier(request)
            allowed, retry_after = RateLimiter.check_rate_limit(
                identifier, req_limit, req_period, scope
            )

            if not allowed:
                response = Response(
                    {
                        'status': 'error',
                        'error': {
                            'code': 'RATE_LIMIT_EXCEEDED',
                            'message': f'Rate limit exceeded. Try again in {retry_after} seconds.',
                            'retry_after': retry_after,
                        }
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
                response['Retry-After'] = str(retry_after)
                return response

            # Execute view
            response = view_func(request, *args, **kwargs)

            # Add rate limit headers
            headers = RateLimiter.get_rate_limit_headers(
                identifier, req_limit, req_period, scope
            )
            for header, value in headers.items():
                response[header] = value

            return response

        return wrapped_view

    return decorator


class RateLimitMixin:
    """
    Mixin for DRF ViewSets to add rate limiting.

    Usage:
        class MyViewSet(RateLimitMixin, viewsets.ModelViewSet):
            ratelimit_scope = 'api'
            ratelimit_limit = 100
            ratelimit_period = 3600
    """

    ratelimit_scope = 'api'
    ratelimit_limit = None  # Use defaults
    ratelimit_period = None  # Use defaults

    def initial(self, request, *args, **kwargs):
        """Check rate limit before processing request."""
        super().initial(request, *args, **kwargs)

        # Get limits
        if self.ratelimit_limit is None or self.ratelimit_period is None:
            if request.user and request.user.is_authenticated:
                limit = 1000
                period = 3600
            else:
                limit = 100
                period = 3600
        else:
            limit = self.ratelimit_limit
            period = self.ratelimit_period

        # Check rate limit
        identifier = RateLimiter.get_identifier(request)
        allowed, retry_after = RateLimiter.check_rate_limit(
            identifier, limit, period, self.ratelimit_scope
        )

        if not allowed:
            from rest_framework.exceptions import Throttled
            raise Throttled(wait=retry_after)

    def finalize_response(self, request, response, *args, **kwargs):
        """Add rate limit headers to response."""
        response = super().finalize_response(request, response, *args, **kwargs)

        # Get limits
        if self.ratelimit_limit is None or self.ratelimit_period is None:
            if request.user and request.user.is_authenticated:
                limit = 1000
                period = 3600
            else:
                limit = 100
                period = 3600
        else:
            limit = self.ratelimit_limit
            period = self.ratelimit_period

        # Add headers
        identifier = RateLimiter.get_identifier(request)
        headers = RateLimiter.get_rate_limit_headers(
            identifier, limit, period, self.ratelimit_scope
        )

        for header, value in headers.items():
            response[header] = value

        return response


def get_client_ip(request):
    """
    Get client IP address from request.
    Handles proxies and load balancers.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
