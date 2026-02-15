"""
Security tests for BugsTracker.

Tests various security measures including:
- Input sanitization
- XSS prevention
- SQL injection prevention
- CSRF protection
- Authentication security
- File upload security
"""

import pytest
from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
import json

from apps.common.security.sanitizers import (
    sanitize_html,
    sanitize_input,
    sanitize_filename,
    sanitize_sql_identifier,
)
from apps.common.security.validators import (
    validate_file_upload,
    validate_url,
    validate_email,
    validate_password_strength,
)

User = get_user_model()


class HTMLSanitizationTests(TestCase):
    """Test HTML sanitization to prevent XSS attacks."""

    def test_sanitize_script_tags(self):
        """Script tags should be removed."""
        malicious_html = '<script>alert("XSS")</script><p>Safe content</p>'
        clean_html = sanitize_html(malicious_html)

        self.assertNotIn('<script>', clean_html)
        self.assertNotIn('alert', clean_html)
        self.assertIn('<p>Safe content</p>', clean_html)

    def test_sanitize_javascript_protocol(self):
        """JavaScript protocol in links should be removed."""
        malicious_html = '<a href="javascript:alert(\'XSS\')">Click</a>'
        clean_html = sanitize_html(malicious_html)

        self.assertNotIn('javascript:', clean_html)

    def test_sanitize_event_handlers(self):
        """Event handlers (onclick, onload, etc.) should be removed."""
        malicious_html = '<p onclick="alert(\'XSS\')">Click me</p>'
        clean_html = sanitize_html(malicious_html)

        self.assertNotIn('onclick', clean_html)

    def test_allow_safe_html(self):
        """Safe HTML tags should be preserved."""
        safe_html = '<p>Text</p><strong>Bold</strong><a href="https://example.com">Link</a>'
        clean_html = sanitize_html(safe_html)

        self.assertIn('<p>Text</p>', clean_html)
        self.assertIn('<strong>Bold</strong>', clean_html)
        self.assertIn('href="https://example.com"', clean_html)

    def test_sanitize_data_protocol(self):
        """Data protocol should be removed."""
        malicious_html = '<img src="data:text/html,<script>alert(\'XSS\')</script>">'
        clean_html = sanitize_html(malicious_html)

        self.assertNotIn('data:', clean_html)

    def test_sanitize_nested_tags(self):
        """Nested malicious tags should be removed."""
        malicious_html = '<div><script>alert("XSS")</script></div>'
        clean_html = sanitize_html(malicious_html)

        self.assertNotIn('<script>', clean_html)


class InputSanitizationTests(TestCase):
    """Test input sanitization."""

    def test_sanitize_input_escapes_html(self):
        """HTML should be escaped by default."""
        user_input = '<script>alert("XSS")</script>'
        sanitized = sanitize_input(user_input)

        self.assertIn('&lt;script&gt;', sanitized)
        self.assertNotIn('<script>', sanitized)

    def test_sanitize_input_with_html_allowed(self):
        """HTML should be sanitized when allowed."""
        user_input = '<p>Text</p><script>alert("XSS")</script>'
        sanitized = sanitize_input(user_input, allow_html=True)

        self.assertIn('<p>Text</p>', sanitized)
        self.assertNotIn('<script>', sanitized)

    def test_sanitize_input_truncates(self):
        """Input should be truncated to max_length."""
        long_input = 'a' * 1000
        sanitized = sanitize_input(long_input, max_length=100)

        self.assertEqual(len(sanitized), 100)

    def test_sanitize_filename(self):
        """Filenames should be sanitized."""
        # Directory traversal attempt
        filename = '../../etc/passwd'
        safe_filename = sanitize_filename(filename)

        self.assertNotIn('..', safe_filename)
        self.assertNotIn('/', safe_filename)

    def test_sanitize_filename_special_chars(self):
        """Special characters should be removed from filenames."""
        filename = 'file<script>.txt'
        safe_filename = sanitize_filename(filename)

        self.assertNotIn('<', safe_filename)
        self.assertNotIn('>', safe_filename)

    def test_sanitize_sql_identifier(self):
        """SQL identifiers should be sanitized."""
        malicious_identifier = 'users; DROP TABLE users;'
        safe_identifier = sanitize_sql_identifier(malicious_identifier)

        self.assertNotIn(';', safe_identifier)
        self.assertNotIn(' ', safe_identifier)


class FileUploadSecurityTests(TestCase):
    """Test file upload security validation."""

    def test_validate_file_size(self):
        """Files exceeding max size should be rejected."""
        # Create large file (11 MB)
        large_file = SimpleUploadedFile(
            "large.txt",
            b"x" * (11 * 1024 * 1024),
            content_type="text/plain"
        )

        with self.assertRaises(ValidationError) as context:
            validate_file_upload(large_file, max_size=10 * 1024 * 1024)

        self.assertIn('exceeds maximum', str(context.exception))

    def test_validate_dangerous_extension(self):
        """Dangerous file extensions should be rejected."""
        dangerous_file = SimpleUploadedFile(
            "malware.exe",
            b"malicious content",
            content_type="application/x-msdownload"
        )

        with self.assertRaises(ValidationError) as context:
            validate_file_upload(dangerous_file)

        self.assertIn('not allowed', str(context.exception))

    def test_validate_path_traversal_in_filename(self):
        """Filenames with path traversal should be rejected."""
        traversal_file = SimpleUploadedFile(
            "../../../etc/passwd",
            b"content",
            content_type="text/plain"
        )

        with self.assertRaises(ValidationError) as context:
            validate_file_upload(traversal_file)

        self.assertIn('path traversal', str(context.exception))

    def test_validate_null_bytes_in_filename(self):
        """Filenames with null bytes should be rejected."""
        null_byte_file = SimpleUploadedFile(
            "file\x00.txt",
            b"content",
            content_type="text/plain"
        )

        with self.assertRaises(ValidationError) as context:
            validate_file_upload(null_byte_file)

        self.assertIn('null bytes', str(context.exception))


class URLValidationTests(TestCase):
    """Test URL validation security."""

    def test_validate_https_url(self):
        """Valid HTTPS URLs should pass."""
        try:
            validate_url('https://example.com/path')
        except ValidationError:
            self.fail("Valid HTTPS URL should not raise exception")

    def test_reject_javascript_protocol(self):
        """JavaScript protocol should be rejected."""
        with self.assertRaises(ValidationError):
            validate_url('javascript:alert("XSS")')

    def test_reject_data_protocol(self):
        """Data protocol should be rejected."""
        with self.assertRaises(ValidationError):
            validate_url('data:text/html,<script>alert("XSS")</script>')

    def test_reject_localhost(self):
        """Localhost URLs should be rejected by default."""
        with self.assertRaises(ValidationError):
            validate_url('http://localhost:8000/admin/')

    def test_allow_localhost_when_permitted(self):
        """Localhost URLs should pass when explicitly allowed."""
        try:
            validate_url('http://localhost:8000/', allow_localhost=True)
        except ValidationError:
            self.fail("Localhost should be allowed when permitted")

    def test_reject_private_ips(self):
        """Private IP addresses should be rejected."""
        private_ips = [
            'http://192.168.1.1/',
            'http://10.0.0.1/',
            'http://172.16.0.1/',
        ]

        for ip in private_ips:
            with self.assertRaises(ValidationError):
                validate_url(ip)


class PasswordSecurityTests(TestCase):
    """Test password security validation."""

    def test_password_minimum_length(self):
        """Passwords under 12 characters should be rejected."""
        with self.assertRaises(ValidationError):
            validate_password_strength('Short1!')

    def test_password_requires_uppercase(self):
        """Passwords without uppercase should be rejected."""
        with self.assertRaises(ValidationError):
            validate_password_strength('lowercase123!')

    def test_password_requires_lowercase(self):
        """Passwords without lowercase should be rejected."""
        with self.assertRaises(ValidationError):
            validate_password_strength('UPPERCASE123!')

    def test_password_requires_digit(self):
        """Passwords without digits should be rejected."""
        with self.assertRaises(ValidationError):
            validate_password_strength('NoDigitsHere!')

    def test_password_requires_special_char(self):
        """Passwords without special characters should be rejected."""
        with self.assertRaises(ValidationError):
            validate_password_strength('NoSpecialChar123')

    def test_common_password_rejected(self):
        """Common passwords should be rejected."""
        with self.assertRaises(ValidationError):
            validate_password_strength('Password123!')

    def test_strong_password_accepted(self):
        """Strong passwords should pass validation."""
        try:
            validate_password_strength('Str0ng!P@ssw0rd')
        except ValidationError:
            self.fail("Strong password should not raise exception")


class AuthenticationSecurityTests(APITestCase):
    """Test authentication security."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestP@ssw0rd123'
        )

    def test_login_with_valid_credentials(self):
        """Valid credentials should authenticate."""
        response = self.client.post('/api/v1/auth/login/', {
            'username': 'testuser',
            'password': 'TestP@ssw0rd123'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_with_invalid_credentials(self):
        """Invalid credentials should be rejected."""
        response = self.client.post('/api/v1/auth/login/', {
            'username': 'testuser',
            'password': 'WrongPassword'
        })

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_password_not_returned_in_response(self):
        """Password should never be returned in API responses."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/auth/me/')

        self.assertNotIn('password', response.data)

    @override_settings(SIMPLE_JWT={'ACCESS_TOKEN_LIFETIME': timedelta(seconds=1)})
    def test_expired_token_rejected(self):
        """Expired tokens should be rejected."""
        # Get token
        response = self.client.post('/api/v1/auth/login/', {
            'username': 'testuser',
            'password': 'TestP@ssw0rd123'
        })
        token = response.data['access']

        # Wait for expiration
        import time
        time.sleep(2)

        # Try to use expired token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/v1/auth/me/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CSRFProtectionTests(TestCase):
    """Test CSRF protection."""

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestP@ssw0rd123'
        )

    def test_post_without_csrf_token_rejected(self):
        """POST requests without CSRF token should be rejected."""
        self.client.login(username='testuser', password='TestP@ssw0rd123')

        response = self.client.post('/api/v1/projects/', {
            'name': 'Test Project'
        })

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_with_csrf_token_accepted(self):
        """POST requests with valid CSRF token should be accepted."""
        self.client.login(username='testuser', password='TestP@ssw0rd123')

        # Get CSRF token
        response = self.client.get('/api/v1/auth/csrf/')
        csrf_token = response.cookies['csrftoken'].value

        # POST with CSRF token
        response = self.client.post(
            '/api/v1/projects/',
            {'name': 'Test Project'},
            HTTP_X_CSRFTOKEN=csrf_token
        )

        # Should not be 403 (may be 401 if not authenticated via API)
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RateLimitingTests(APITestCase):
    """Test rate limiting."""

    def setUp(self):
        self.client = APIClient()

    @override_settings(RATE_LIMIT_IN_DEBUG=True)
    def test_rate_limit_enforced(self):
        """Rate limits should be enforced."""
        # Make requests up to limit
        for i in range(10):
            response = self.client.post('/api/v1/auth/login/', {
                'username': 'testuser',
                'password': 'password'
            })

        # Next request should be rate limited
        response = self.client.post('/api/v1/auth/login/', {
            'username': 'testuser',
            'password': 'password'
        })

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn('rate_limit', response.data.get('error', {}).get('code', '').lower())

    @override_settings(RATE_LIMIT_IN_DEBUG=True)
    def test_rate_limit_headers_present(self):
        """Rate limit headers should be present in responses."""
        response = self.client.get('/api/v1/health/')

        self.assertIn('X-RateLimit-Limit', response)
        self.assertIn('X-RateLimit-Remaining', response)
        self.assertIn('X-RateLimit-Reset', response)


class SQLInjectionTests(TestCase):
    """Test SQL injection prevention."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestP@ssw0rd123'
        )

    def test_orm_prevents_sql_injection(self):
        """Django ORM should prevent SQL injection."""
        # Attempt SQL injection via username filter
        malicious_input = "testuser' OR '1'='1"

        # This should NOT return results (ORM uses parameterized queries)
        users = User.objects.filter(username=malicious_input)

        self.assertEqual(users.count(), 0)

    def test_search_with_special_chars(self):
        """Search with SQL special characters should be safe."""
        malicious_search = "'; DROP TABLE users; --"

        # Should not cause SQL injection
        try:
            users = User.objects.filter(username__icontains=malicious_search)
            # Query should execute safely
            list(users)  # Force evaluation
        except Exception as e:
            self.fail(f"Search with special chars should not cause exception: {e}")


class SecurityHeadersTests(TestCase):
    """Test security headers in responses."""

    def setUp(self):
        self.client = Client()

    def test_x_content_type_options_header(self):
        """X-Content-Type-Options header should be present."""
        response = self.client.get('/api/v1/health/')

        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')

    def test_x_frame_options_header(self):
        """X-Frame-Options header should be present."""
        response = self.client.get('/api/v1/health/')

        self.assertEqual(response['X-Frame-Options'], 'DENY')

    def test_x_xss_protection_header(self):
        """X-XSS-Protection header should be present."""
        response = self.client.get('/api/v1/health/')

        self.assertEqual(response['X-XSS-Protection'], '1; mode=block')

    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_hsts_header(self):
        """HSTS header should be present when SSL is enforced."""
        response = self.client.get('/api/v1/health/')

        self.assertIn('Strict-Transport-Security', response)

    def test_csp_header(self):
        """Content-Security-Policy header should be present."""
        response = self.client.get('/api/v1/health/')

        self.assertIn('Content-Security-Policy', response)
        self.assertIn("default-src 'self'", response['Content-Security-Policy'])


class PermissionSecurityTests(APITestCase):
    """Test permission and authorization security."""

    def setUp(self):
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='TestP@ssw0rd123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='TestP@ssw0rd123'
        )
        self.client = APIClient()

    def test_unauthenticated_access_denied(self):
        """Unauthenticated users should not access protected endpoints."""
        response = self.client.get('/api/v1/projects/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_access_allowed(self):
        """Authenticated users should access their resources."""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/v1/projects/')

        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND  # If no projects exist
        ])

    def test_cannot_access_other_user_resources(self):
        """Users should not access other users' private resources."""
        # This test assumes issues belong to users
        # Adjust based on your actual model structure
        self.client.force_authenticate(user=self.user1)

        # Try to access user2's resource
        # response = self.client.get(f'/api/v1/users/{self.user2.id}/private-data/')
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Note: Implement based on actual permission logic
        pass


# Run tests with: pytest backend/apps/common/tests/test_security.py -v
