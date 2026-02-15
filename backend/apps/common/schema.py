"""
OpenAPI schema customizations and extensions.
"""

from drf_spectacular.extensions import OpenApiSerializerExtension
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiExample, OpenApiParameter
from rest_framework import serializers


# Common OpenAPI examples for reuse

# Authentication examples
AUTH_LOGIN_EXAMPLE = OpenApiExample(
    'Login Example',
    value={
        'email': 'user@example.com',
        'password': 'SecurePassword123!'
    },
    request_only=True,
)

AUTH_LOGIN_RESPONSE_EXAMPLE = OpenApiExample(
    'Login Success',
    value={
        'status': 'success',
        'data': {
            'access': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
            'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
            'user': {
                'id': '550e8400-e29b-41d4-a716-446655440000',
                'email': 'user@example.com',
                'full_name': 'John Doe',
                'is_active': True,
            }
        },
        'message': 'Login successful'
    },
    response_only=True,
    status_codes=['200'],
)

# Issue examples
ISSUE_CREATE_EXAMPLE = OpenApiExample(
    'Create Issue',
    value={
        'project': '550e8400-e29b-41d4-a716-446655440000',
        'issue_type': 'task',
        'summary': 'Implement user authentication',
        'description': 'Add JWT-based authentication to the API',
        'priority': 'high',
        'assignee': '550e8400-e29b-41d4-a716-446655440001',
        'labels': ['backend', 'security'],
        'custom_fields': {
            'story_points': 5,
            'component': 'Authentication'
        }
    },
    request_only=True,
)

ISSUE_RESPONSE_EXAMPLE = OpenApiExample(
    'Issue Created',
    value={
        'status': 'success',
        'data': {
            'id': '550e8400-e29b-41d4-a716-446655440002',
            'key': 'PROJ-123',
            'project': {
                'id': '550e8400-e29b-41d4-a716-446655440000',
                'key': 'PROJ',
                'name': 'My Project'
            },
            'issue_type': 'task',
            'summary': 'Implement user authentication',
            'description': 'Add JWT-based authentication to the API',
            'status': 'to_do',
            'priority': 'high',
            'assignee': {
                'id': '550e8400-e29b-41d4-a716-446655440001',
                'email': 'developer@example.com',
                'full_name': 'Jane Developer'
            },
            'reporter': {
                'id': '550e8400-e29b-41d4-a716-446655440003',
                'email': 'manager@example.com',
                'full_name': 'Bob Manager'
            },
            'labels': ['backend', 'security'],
            'custom_fields': {
                'story_points': 5,
                'component': 'Authentication'
            },
            'created_at': '2026-02-15T10:30:00.000Z',
            'updated_at': '2026-02-15T10:30:00.000Z'
        },
        'message': 'Issue created successfully'
    },
    response_only=True,
    status_codes=['201'],
)

# JQL search example
JQL_SEARCH_EXAMPLE = OpenApiExample(
    'JQL Search',
    value={
        'jql': 'project = "PROJ" AND status = "in_progress" AND assignee = currentUser()',
        'fields': ['id', 'key', 'summary', 'status', 'assignee'],
        'max_results': 50,
        'start_at': 0
    },
    request_only=True,
)

# Pagination example
PAGINATION_RESPONSE_EXAMPLE = OpenApiExample(
    'Paginated Response',
    value={
        'count': 100,
        'next': 'http://api.example.com/api/v1/issues/?page=3',
        'previous': 'http://api.example.com/api/v1/issues/?page=1',
        'results': [
            {
                'id': '550e8400-e29b-41d4-a716-446655440002',
                'key': 'PROJ-123',
                'summary': 'Implement user authentication',
                'status': 'in_progress'
            }
        ]
    },
    response_only=True,
    status_codes=['200'],
)

# Error examples
ERROR_400_EXAMPLE = OpenApiExample(
    'Validation Error',
    value={
        'status': 'error',
        'error': {
            'code': 'VALIDATION_ERROR',
            'message': 'Invalid input data',
            'details': {
                'email': ['This field is required.'],
                'password': ['This field must be at least 8 characters.']
            }
        }
    },
    response_only=True,
    status_codes=['400'],
)

ERROR_401_EXAMPLE = OpenApiExample(
    'Authentication Error',
    value={
        'status': 'error',
        'error': {
            'code': 'AUTHENTICATION_ERROR',
            'message': 'Authentication credentials were not provided.'
        }
    },
    response_only=True,
    status_codes=['401'],
)

ERROR_403_EXAMPLE = OpenApiExample(
    'Permission Denied',
    value={
        'status': 'error',
        'error': {
            'code': 'PERMISSION_DENIED',
            'message': 'You do not have permission to perform this action.'
        }
    },
    response_only=True,
    status_codes=['403'],
)

ERROR_404_EXAMPLE = OpenApiExample(
    'Not Found',
    value={
        'status': 'error',
        'error': {
            'code': 'NOT_FOUND',
            'message': 'The requested resource was not found.'
        }
    },
    response_only=True,
    status_codes=['404'],
)

ERROR_429_EXAMPLE = OpenApiExample(
    'Rate Limit Exceeded',
    value={
        'status': 'error',
        'error': {
            'code': 'RATE_LIMIT_EXCEEDED',
            'message': 'Rate limit exceeded. Try again in 3600 seconds.',
            'retry_after': 3600
        }
    },
    response_only=True,
    status_codes=['429'],
)

ERROR_500_EXAMPLE = OpenApiExample(
    'Server Error',
    value={
        'status': 'error',
        'error': {
            'code': 'SERVER_ERROR',
            'message': 'An internal server error occurred. Please try again later.'
        }
    },
    response_only=True,
    status_codes=['500'],
)


# Common OpenAPI parameters

ORGANIZATION_HEADER_PARAM = OpenApiParameter(
    name='X-Organization-ID',
    type=str,
    location=OpenApiParameter.HEADER,
    description='Organization UUID for multi-tenant isolation (optional if user belongs to single org)',
    required=False,
)

PAGE_PARAM = OpenApiParameter(
    name='page',
    type=int,
    location=OpenApiParameter.QUERY,
    description='Page number for pagination',
    required=False,
)

PAGE_SIZE_PARAM = OpenApiParameter(
    name='page_size',
    type=int,
    location=OpenApiParameter.QUERY,
    description='Number of results per page (max: 100)',
    required=False,
)

SEARCH_PARAM = OpenApiParameter(
    name='search',
    type=str,
    location=OpenApiParameter.QUERY,
    description='Search query string',
    required=False,
)

ORDERING_PARAM = OpenApiParameter(
    name='ordering',
    type=str,
    location=OpenApiParameter.QUERY,
    description='Field to order results by (prefix with - for descending)',
    required=False,
)

FIELDS_PARAM = OpenApiParameter(
    name='fields',
    type=str,
    location=OpenApiParameter.QUERY,
    description='Comma-separated list of fields to include in response',
    required=False,
)


class CustomAutoSchema(AutoSchema):
    """
    Custom AutoSchema with additional metadata.
    """

    def get_operation_id(self):
        """Generate operation ID with version prefix."""
        operation_id = super().get_operation_id()
        # Add version prefix if not already present
        if not operation_id.startswith('v1_'):
            operation_id = f'v1_{operation_id}'
        return operation_id

    def get_tags(self):
        """Get tags from view metadata."""
        tags = super().get_tags()

        # Add version tag
        if hasattr(self.view, 'api_version'):
            tags.append(f'v{self.view.api_version}')

        return tags


def extend_schema_with_examples(
    summary=None,
    description=None,
    request_example=None,
    response_examples=None,
    parameters=None,
    **kwargs
):
    """
    Helper function to extend schema with common examples and parameters.

    Usage:
        @extend_schema_with_examples(
            summary='Create Issue',
            request_example=ISSUE_CREATE_EXAMPLE,
            response_examples=[ISSUE_RESPONSE_EXAMPLE, ERROR_400_EXAMPLE],
        )
        def create(self, request):
            ...
    """
    examples = []

    if request_example:
        examples.append(request_example)

    if response_examples:
        examples.extend(response_examples)

    # Add common error examples
    if response_examples and not any(ex.status_codes == ['401'] for ex in examples):
        examples.append(ERROR_401_EXAMPLE)

    if response_examples and not any(ex.status_codes == ['403'] for ex in examples):
        examples.append(ERROR_403_EXAMPLE)

    # Build parameters list
    params = parameters or []

    return extend_schema(
        summary=summary,
        description=description,
        examples=examples,
        parameters=params,
        **kwargs
    )


# Decorator for common list view schema
def list_schema(model_name, parameters=None):
    """
    Schema decorator for list views.
    """
    params = [PAGE_PARAM, PAGE_SIZE_PARAM, SEARCH_PARAM, ORDERING_PARAM, FIELDS_PARAM]
    if parameters:
        params.extend(parameters)

    return extend_schema(
        summary=f'List {model_name}s',
        description=f'Retrieve a paginated list of {model_name}s.',
        parameters=params,
        examples=[PAGINATION_RESPONSE_EXAMPLE, ERROR_401_EXAMPLE],
    )


# Decorator for common retrieve view schema
def retrieve_schema(model_name):
    """
    Schema decorator for retrieve views.
    """
    return extend_schema(
        summary=f'Retrieve {model_name}',
        description=f'Retrieve details of a specific {model_name}.',
        examples=[ERROR_401_EXAMPLE, ERROR_403_EXAMPLE, ERROR_404_EXAMPLE],
    )


# Decorator for common create view schema
def create_schema(model_name):
    """
    Schema decorator for create views.
    """
    return extend_schema(
        summary=f'Create {model_name}',
        description=f'Create a new {model_name}.',
        examples=[ERROR_400_EXAMPLE, ERROR_401_EXAMPLE, ERROR_403_EXAMPLE],
    )


# Decorator for common update view schema
def update_schema(model_name):
    """
    Schema decorator for update views.
    """
    return extend_schema(
        summary=f'Update {model_name}',
        description=f'Update an existing {model_name}.',
        examples=[ERROR_400_EXAMPLE, ERROR_401_EXAMPLE, ERROR_403_EXAMPLE, ERROR_404_EXAMPLE],
    )


# Decorator for common delete view schema
def delete_schema(model_name):
    """
    Schema decorator for delete views.
    """
    return extend_schema(
        summary=f'Delete {model_name}',
        description=f'Delete a {model_name}.',
        examples=[ERROR_401_EXAMPLE, ERROR_403_EXAMPLE, ERROR_404_EXAMPLE],
    )
