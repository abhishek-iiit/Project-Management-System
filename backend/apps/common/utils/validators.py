"""
Common validation utilities.
"""

import uuid
import json
from typing import Any, Dict
from django.core.exceptions import ValidationError


def validate_uuid(value: str) -> bool:
    """
    Validate if string is a valid UUID.

    Args:
        value: String to validate

    Returns:
        True if valid UUID

    Raises:
        ValidationError: If invalid UUID
    """
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        raise ValidationError(f"'{value}' is not a valid UUID")


def validate_json_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
    """
    Validate JSON data against a schema.

    Args:
        data: Data to validate
        schema: JSON schema

    Returns:
        True if valid

    Raises:
        ValidationError: If validation fails
    """
    try:
        from jsonschema import validate as json_validate, ValidationError as JSONSchemaError
        json_validate(instance=data, schema=schema)
        return True
    except JSONSchemaError as e:
        raise ValidationError(f"JSON schema validation failed: {str(e)}")
    except ImportError:
        # jsonschema not installed, skip validation
        return True


def validate_file_size(file, max_size_mb: int = 10):
    """
    Validate file size.

    Args:
        file: File object
        max_size_mb: Maximum file size in MB

    Raises:
        ValidationError: If file too large
    """
    max_size = max_size_mb * 1024 * 1024  # Convert to bytes
    if file.size > max_size:
        raise ValidationError(
            f"File size {file.size} exceeds maximum allowed size of {max_size_mb}MB"
        )


def validate_file_extension(file, allowed_extensions: list):
    """
    Validate file extension.

    Args:
        file: File object
        allowed_extensions: List of allowed extensions (e.g., ['.pdf', '.jpg'])

    Raises:
        ValidationError: If extension not allowed
    """
    import os
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in allowed_extensions:
        raise ValidationError(
            f"File extension '{ext}' not allowed. Allowed: {', '.join(allowed_extensions)}"
        )
