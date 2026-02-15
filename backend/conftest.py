"""
Global pytest configuration and fixtures for BugsTracker.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from faker import Faker

# Initialize Faker
fake = Faker()

User = get_user_model()


# ============================================================================
# Pytest Configuration Hooks
# ============================================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "api: API endpoint tests")
    config.addinivalue_line("markers", "model: Model tests")
    config.addinivalue_line("markers", "service: Service layer tests")
    config.addinivalue_line("markers", "slow: Slow running tests")


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Enable database access for all tests."""
    pass


# ============================================================================
# User Fixtures
# ============================================================================

@pytest.fixture
def user(db):
    """Create and return a test user."""
    return User.objects.create_user(
        email='test@example.com',
        password='testpass123',
        full_name='Test User',
        is_active=True
    )


@pytest.fixture
def users(db):
    """Create multiple test users."""
    return [
        User.objects.create_user(
            email=f'user{i}@example.com',
            password='testpass123',
            full_name=f'Test User {i}',
            is_active=True
        )
        for i in range(1, 6)
    ]


@pytest.fixture
def admin_user(db):
    """Create and return an admin user."""
    return User.objects.create_superuser(
        email='admin@example.com',
        password='adminpass123',
        full_name='Admin User'
    )


@pytest.fixture
def inactive_user(db):
    """Create an inactive user."""
    return User.objects.create_user(
        email='inactive@example.com',
        password='testpass123',
        full_name='Inactive User',
        is_active=False
    )


# ============================================================================
# API Client Fixtures
# ============================================================================

@pytest.fixture
def api_client():
    """Return DRF API client."""
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, user):
    """Return API client authenticated with JWT."""
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
    api_client.user = user
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """Return API client authenticated as admin."""
    refresh = RefreshToken.for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
    api_client.user = admin_user
    return api_client


# ============================================================================
# Organization Fixtures
# ============================================================================

@pytest.fixture
def organization(db, user):
    """Create and return test organization."""
    from apps.organizations.models import Organization, OrganizationMember

    org = Organization.objects.create(
        name='Test Organization',
        slug='test-org',
        description='Test organization description',
        is_active=True
    )

    OrganizationMember.objects.create(
        organization=org,
        user=user,
        role='admin',
        is_active=True
    )

    return org


@pytest.fixture
def organizations(db, users):
    """Create multiple test organizations."""
    from apps.organizations.models import Organization, OrganizationMember

    orgs = []
    for i, user in enumerate(users[:3], 1):
        org = Organization.objects.create(
            name=f'Test Organization {i}',
            slug=f'test-org-{i}',
            description=f'Test organization {i}',
            is_active=True
        )

        OrganizationMember.objects.create(
            organization=org,
            user=user,
            role='admin',
            is_active=True
        )

        orgs.append(org)

    return orgs


# ============================================================================
# Project Fixtures
# ============================================================================

@pytest.fixture
def project(db, organization, user):
    """Create and return test project."""
    from apps.projects.models import Project, ProjectMember

    proj = Project.objects.create(
        name='Test Project',
        key='TEST',
        organization=organization,
        description='Test project description',
        is_active=True
    )

    ProjectMember.objects.create(
        project=proj,
        user=user,
        role='admin',
        is_active=True
    )

    return proj


@pytest.fixture
def projects(db, organization, users):
    """Create multiple test projects."""
    from apps.projects.models import Project, ProjectMember

    project_list = []
    for i in range(1, 4):
        proj = Project.objects.create(
            name=f'Test Project {i}',
            key=f'TEST{i}',
            organization=organization,
            description=f'Test project {i}',
            is_active=True
        )

        if users:
            ProjectMember.objects.create(
                project=proj,
                user=users[0],
                role='admin',
                is_active=True
            )

        project_list.append(proj)

    return project_list


# ============================================================================
# Issue Fixtures
# ============================================================================

@pytest.fixture
def issue(db, project, user):
    """Create a test issue."""
    from apps.issues.models import Issue

    return Issue.objects.create(
        project=project,
        reporter=user,
        assignee=user,
        summary='Test issue',
        description='Test issue description',
        issue_type='task',
        priority='medium',
        status='to_do'
    )


@pytest.fixture
def issues(db, project, users):
    """Create multiple test issues."""
    from apps.issues.models import Issue

    issue_list = []
    for i in range(1, 11):
        issue = Issue.objects.create(
            project=project,
            reporter=users[0] if users else None,
            assignee=users[i % len(users)] if users else None,
            summary=f'Test issue {i}',
            description=f'Test issue {i} description',
            issue_type=['task', 'bug', 'story'][i % 3],
            priority=['low', 'medium', 'high'][i % 3],
            status=['to_do', 'in_progress', 'done'][i % 3]
        )
        issue_list.append(issue)

    return issue_list


# ============================================================================
# Helper Fixtures
# ============================================================================

@pytest.fixture
def faker():
    """Provide Faker instance."""
    return fake


@pytest.fixture
def mock_request(user):
    """Create a mock request object."""
    from django.test import RequestFactory

    factory = RequestFactory()
    request = factory.get('/')
    request.user = user
    return request


@pytest.fixture
def file_upload():
    """Create a mock file upload."""
    from django.core.files.uploadedfile import SimpleUploadedFile
    return SimpleUploadedFile(
        'test.txt',
        b'test file content',
        content_type='text/plain'
    )


# ============================================================================
# Performance Testing Fixtures
# ============================================================================

@pytest.fixture
def assert_num_queries():
    """Assert number of database queries."""
    from django.test.utils import CaptureQueriesContext
    from django.db import connection

    class AssertNumQueries:
        def __init__(self):
            self.context = CaptureQueriesContext(connection)

        def __enter__(self):
            self.context.__enter__()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.context.__exit__(exc_type, exc_val, exc_tb)

        def assert_max_queries(self, num):
            """Assert maximum number of queries."""
            actual = len(self.context.captured_queries)
            assert actual <= num, f"Expected max {num} queries, got {actual}"

        def assert_queries(self, num):
            """Assert exact number of queries."""
            actual = len(self.context.captured_queries)
            assert actual == num, f"Expected {num} queries, got {actual}"

    return AssertNumQueries()


# ============================================================================
# Cleanup Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_files():
    """Clean up test files after each test."""
    yield
    import shutil
    from django.conf import settings
    media_root = settings.MEDIA_ROOT
    if media_root.exists() and 'test' in str(media_root):
        shutil.rmtree(media_root, ignore_errors=True)
