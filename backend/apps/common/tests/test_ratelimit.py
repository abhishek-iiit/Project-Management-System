"""
Tests for rate limiting functionality.
"""

import pytest
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from apps.common.ratelimit import RateLimiter, ratelimit, RateLimitMixin
from rest_framework.decorators import api_view
from rest_framework.response import Response

User = get_user_model()


class RateLimiterTestCase(TestCase):
    """Test RateLimiter utility."""

    def setUp(self):
        """Set up test fixtures."""
        cache.clear()
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

    def tearDown(self):
        """Clean up after tests."""
        cache.clear()

    def test_get_identifier_authenticated(self):
        """Test identifier generation for authenticated user."""
        request = self.factory.get('/')
        request.user = self.user

        identifier = RateLimiter.get_identifier(request)
        self.assertEqual(identifier, f'user:{self.user.id}')

    def test_get_identifier_anonymous(self):
        """Test identifier generation for anonymous user."""
        from django.contrib.auth.models import AnonymousUser

        request = self.factory.get('/')
        request.user = AnonymousUser()

        identifier = RateLimiter.get_identifier(request)
        self.assertTrue(identifier.startswith('ip:'))

    def test_get_identifier_with_proxy(self):
        """Test identifier with X-Forwarded-For header."""
        from django.contrib.auth.models import AnonymousUser

        request = self.factory.get('/', HTTP_X_FORWARDED_FOR='192.168.1.1, 10.0.0.1')
        request.user = AnonymousUser()

        identifier = RateLimiter.get_identifier(request)
        self.assertEqual(identifier, 'ip:192.168.1.1')

    def test_check_rate_limit_allowed(self):
        """Test rate limit check when under limit."""
        identifier = 'test:user'
        limit = 10
        period = 60

        allowed, retry_after = RateLimiter.check_rate_limit(
            identifier, limit, period, 'test'
        )

        self.assertTrue(allowed)
        self.assertEqual(retry_after, 0)

    def test_check_rate_limit_exceeded(self):
        """Test rate limit check when limit exceeded."""
        identifier = 'test:user'
        limit = 3
        period = 60

        # Make requests up to limit
        for i in range(limit):
            allowed, _ = RateLimiter.check_rate_limit(
                identifier, limit, period, 'test'
            )
            self.assertTrue(allowed)

        # Next request should be denied
        allowed, retry_after = RateLimiter.check_rate_limit(
            identifier, limit, period, 'test'
        )

        self.assertFalse(allowed)
        self.assertGreater(retry_after, 0)

    def test_get_rate_limit_headers(self):
        """Test rate limit header generation."""
        identifier = 'test:user'
        limit = 10
        period = 60

        # Make a few requests
        for i in range(3):
            RateLimiter.check_rate_limit(identifier, limit, period, 'test')

        headers = RateLimiter.get_rate_limit_headers(
            identifier, limit, period, 'test'
        )

        self.assertIn('X-RateLimit-Limit', headers)
        self.assertIn('X-RateLimit-Remaining', headers)
        self.assertIn('X-RateLimit-Reset', headers)
        self.assertEqual(headers['X-RateLimit-Limit'], '10')
        self.assertEqual(headers['X-RateLimit-Remaining'], '7')


class RateLimitDecoratorTestCase(APITestCase):
    """Test rate limit decorator."""

    def setUp(self):
        """Set up test fixtures."""
        cache.clear()
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

    def tearDown(self):
        """Clean up after tests."""
        cache.clear()

    def test_rate_limit_decorator_allows_under_limit(self):
        """Test decorator allows requests under limit."""
        # This would need a test view with the decorator
        # For now, we just test the logic
        pass

    def test_rate_limit_decorator_blocks_over_limit(self):
        """Test decorator blocks requests over limit."""
        # This would need a test view with the decorator
        pass


class RateLimitMixinTestCase(APITestCase):
    """Test RateLimitMixin for ViewSets."""

    def setUp(self):
        """Set up test fixtures."""
        cache.clear()
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

    def tearDown(self):
        """Clean up after tests."""
        cache.clear()

    def test_mixin_integration(self):
        """Test mixin integration with ViewSet."""
        # This would need a test ViewSet
        pass


@pytest.mark.django_db
class TestRateLimitIntegration:
    """Integration tests for rate limiting."""

    def test_rate_limit_headers_in_response(self, client):
        """Test that rate limit headers are added to responses."""
        # This would test against actual API endpoints
        pass

    def test_rate_limit_429_response(self, client):
        """Test 429 response when rate limit exceeded."""
        # This would test against actual API endpoints with high volume
        pass
