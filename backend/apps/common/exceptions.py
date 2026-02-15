"""
Custom exception handlers and exceptions.
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404


def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF.

    Returns consistent error response format:
    {
        "status": "error",
        "error": {
            "code": "ERROR_CODE",
            "message": "Error message",
            "details": {}  // Optional
        }
    }
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Customize error response format
        custom_response_data = {
            'status': 'error',
            'error': {
                'code': get_error_code(exc),
                'message': get_error_message(exc, response.data),
            }
        }

        # Add details if available
        if isinstance(response.data, dict) and len(response.data) > 0:
            custom_response_data['error']['details'] = response.data

        response.data = custom_response_data

    else:
        # Handle Django ValidationError
        if isinstance(exc, DjangoValidationError):
            response = Response(
                {
                    'status': 'error',
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'Validation failed',
                        'details': exc.message_dict if hasattr(exc, 'message_dict') else str(exc),
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Handle 404
        elif isinstance(exc, Http404):
            response = Response(
                {
                    'status': 'error',
                    'error': {
                        'code': 'NOT_FOUND',
                        'message': 'Resource not found',
                    }
                },
                status=status.HTTP_404_NOT_FOUND
            )

    return response


def get_error_code(exc):
    """Extract error code from exception."""
    if hasattr(exc, 'default_code'):
        return exc.default_code.upper()
    return exc.__class__.__name__.upper()


def get_error_message(exc, data):
    """Extract error message from exception."""
    if isinstance(data, dict):
        if 'detail' in data:
            return str(data['detail'])
        # Get first error message
        for key, value in data.items():
            if isinstance(value, list) and len(value) > 0:
                return str(value[0])
            return str(value)
    return str(exc)


class BusinessLogicError(Exception):
    """Base exception for business logic errors."""

    def __init__(self, message: str, code: str = 'BUSINESS_LOGIC_ERROR'):
        self.message = message
        self.code = code
        super().__init__(self.message)


class TenantAccessError(Exception):
    """Exception for multi-tenancy access violations."""

    def __init__(self, message: str = 'Access denied to this organization'):
        self.message = message
        super().__init__(self.message)
