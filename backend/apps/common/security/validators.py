"""
Security validators for file uploads, URLs, and other inputs.
"""

import magic
import re
from typing import List, Optional
from urllib.parse import urlparse
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator, EmailValidator as DjangoEmailValidator


# Allowed file MIME types
ALLOWED_IMAGE_TYPES = [
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
    'image/svg+xml',
]

ALLOWED_DOCUMENT_TYPES = [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'text/plain',
    'text/csv',
]

ALLOWED_ARCHIVE_TYPES = [
    'application/zip',
    'application/x-zip-compressed',
    'application/x-tar',
    'application/gzip',
]

# Maximum file sizes (in bytes)
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_DOCUMENT_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_ATTACHMENT_SIZE = 100 * 1024 * 1024  # 100 MB

# Dangerous file extensions
DANGEROUS_EXTENSIONS = [
    'exe', 'bat', 'cmd', 'com', 'pif', 'scr', 'vbs', 'js',
    'jar', 'app', 'deb', 'rpm', 'dmg', 'pkg', 'sh', 'bash',
    'ps1', 'msi', 'gadget', 'dll', 'so', 'dylib'
]


def validate_file_upload(
    file,
    allowed_types: Optional[List[str]] = None,
    max_size: Optional[int] = None,
    check_content: bool = True
) -> None:
    """
    Validate uploaded file for security.

    Args:
        file: Django UploadedFile object
        allowed_types: List of allowed MIME types
        max_size: Maximum file size in bytes
        check_content: Whether to check actual file content (not just extension)

    Raises:
        ValidationError: If file is invalid or potentially malicious

    Examples:
        >>> validate_file_upload(uploaded_file, allowed_types=ALLOWED_IMAGE_TYPES)
    """
    # Check if file exists
    if not file:
        raise ValidationError("No file provided")

    # Get filename and extension
    filename = file.name
    if not filename:
        raise ValidationError("Invalid filename")

    extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

    # Check for dangerous extensions
    if extension in DANGEROUS_EXTENSIONS:
        raise ValidationError(f"File type '.{extension}' is not allowed for security reasons")

    # Check file size
    max_allowed = max_size or MAX_ATTACHMENT_SIZE
    if file.size > max_allowed:
        raise ValidationError(
            f"File size {file.size} bytes exceeds maximum allowed size {max_allowed} bytes"
        )

    # Check MIME type if content checking is enabled
    if check_content:
        # Read file content to determine actual MIME type
        file.seek(0)
        file_content = file.read(2048)  # Read first 2KB
        file.seek(0)  # Reset file pointer

        try:
            mime_type = magic.from_buffer(file_content, mime=True)
        except Exception as e:
            raise ValidationError(f"Unable to determine file type: {str(e)}")

        # Validate MIME type
        allowed = allowed_types or (ALLOWED_IMAGE_TYPES + ALLOWED_DOCUMENT_TYPES + ALLOWED_ARCHIVE_TYPES)
        if mime_type not in allowed:
            raise ValidationError(f"File type '{mime_type}' is not allowed")

        # Additional check: ensure MIME type matches extension
        expected_extensions = {
            'image/jpeg': ['jpg', 'jpeg'],
            'image/png': ['png'],
            'image/gif': ['gif'],
            'image/webp': ['webp'],
            'application/pdf': ['pdf'],
            'application/zip': ['zip'],
            'text/plain': ['txt'],
        }

        if mime_type in expected_extensions:
            if extension not in expected_extensions[mime_type]:
                raise ValidationError(
                    f"File extension '.{extension}' does not match content type '{mime_type}'"
                )

    # Check for null bytes in filename (directory traversal attempt)
    if '\x00' in filename:
        raise ValidationError("Invalid filename: contains null bytes")

    # Check for path traversal attempts
    if '..' in filename or '/' in filename or '\\' in filename:
        raise ValidationError("Invalid filename: path traversal detected")


def validate_image_file(file) -> None:
    """
    Validate uploaded image file.

    Args:
        file: Django UploadedFile object

    Raises:
        ValidationError: If image is invalid
    """
    validate_file_upload(
        file,
        allowed_types=ALLOWED_IMAGE_TYPES,
        max_size=MAX_IMAGE_SIZE,
        check_content=True
    )


def validate_document_file(file) -> None:
    """
    Validate uploaded document file.

    Args:
        file: Django UploadedFile object

    Raises:
        ValidationError: If document is invalid
    """
    validate_file_upload(
        file,
        allowed_types=ALLOWED_DOCUMENT_TYPES,
        max_size=MAX_DOCUMENT_SIZE,
        check_content=True
    )


def validate_url(url: str, allow_localhost: bool = False) -> None:
    """
    Validate URL for security.

    Args:
        url: URL string to validate
        allow_localhost: Whether to allow localhost/127.0.0.1 URLs

    Raises:
        ValidationError: If URL is invalid or potentially malicious

    Examples:
        >>> validate_url('https://example.com/path')
        >>> validate_url('javascript:alert()')  # Raises ValidationError
    """
    if not url:
        raise ValidationError("URL is required")

    # Use Django's URL validator
    validator = URLValidator(
        schemes=['http', 'https']  # Only allow HTTP(S)
    )

    try:
        validator(url)
    except ValidationError as e:
        raise ValidationError(f"Invalid URL: {str(e)}")

    # Parse URL
    parsed = urlparse(url)

    # Check for dangerous protocols
    dangerous_protocols = ['javascript', 'data', 'file', 'vbscript']
    if parsed.scheme.lower() in dangerous_protocols:
        raise ValidationError(f"URL protocol '{parsed.scheme}' is not allowed")

    # Check for localhost/private IPs (unless explicitly allowed)
    if not allow_localhost:
        hostname = parsed.hostname
        if hostname:
            # Check for localhost
            if hostname.lower() in ('localhost', '127.0.0.1', '0.0.0.0', '::1'):
                raise ValidationError("Localhost URLs are not allowed")

            # Check for private IP ranges (basic check)
            if hostname.startswith('192.168.') or hostname.startswith('10.') or hostname.startswith('172.'):
                raise ValidationError("Private IP addresses are not allowed")


def validate_email(email: str) -> None:
    """
    Validate email address.

    Args:
        email: Email address to validate

    Raises:
        ValidationError: If email is invalid

    Examples:
        >>> validate_email('user@example.com')
        >>> validate_email('invalid@')  # Raises ValidationError
    """
    if not email:
        raise ValidationError("Email is required")

    # Use Django's email validator
    validator = DjangoEmailValidator()

    try:
        validator(email)
    except ValidationError as e:
        raise ValidationError(f"Invalid email: {str(e)}")

    # Additional checks
    # Check for disposable email domains (basic list)
    disposable_domains = [
        'tempmail.com', 'throwaway.email', '10minutemail.com',
        'guerrillamail.com', 'mailinator.com', 'maildrop.cc'
    ]

    domain = email.split('@')[-1].lower()
    if domain in disposable_domains:
        raise ValidationError(f"Disposable email addresses are not allowed")


def validate_password_strength(password: str) -> None:
    """
    Validate password strength.

    Requirements:
    - At least 12 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character

    Args:
        password: Password to validate

    Raises:
        ValidationError: If password doesn't meet requirements

    Examples:
        >>> validate_password_strength('SecureP@ssw0rd123')
        >>> validate_password_strength('weak')  # Raises ValidationError
    """
    if not password:
        raise ValidationError("Password is required")

    errors = []

    # Length check
    if len(password) < 12:
        errors.append("Password must be at least 12 characters long")

    # Uppercase check
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")

    # Lowercase check
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")

    # Digit check
    if not re.search(r'\d', password):
        errors.append("Password must contain at least one digit")

    # Special character check
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Password must contain at least one special character")

    # Check for common passwords
    common_passwords = [
        'password123', 'admin123', 'qwerty123', 'letmein123',
        '123456789012', 'password1234'
    ]
    if password.lower() in common_passwords:
        errors.append("Password is too common")

    if errors:
        raise ValidationError(errors)


def validate_api_key_format(api_key: str) -> None:
    """
    Validate API key format.

    Expected format: 64 hexadecimal characters

    Args:
        api_key: API key to validate

    Raises:
        ValidationError: If API key format is invalid
    """
    if not api_key:
        raise ValidationError("API key is required")

    # Check length
    if len(api_key) != 64:
        raise ValidationError("API key must be 64 characters long")

    # Check if hexadecimal
    if not re.match(r'^[a-f0-9]{64}$', api_key.lower()):
        raise ValidationError("API key must be hexadecimal")


def validate_jql_query(query: str) -> None:
    """
    Validate JQL query for basic security.

    Args:
        query: JQL query string

    Raises:
        ValidationError: If query contains dangerous patterns

    Note:
        Full JQL parsing and validation should be done in the search service.
    """
    if not query:
        return

    # Check length
    if len(query) > 10000:
        raise ValidationError("Query is too long (max 10,000 characters)")

    # Check for SQL injection patterns
    dangerous_patterns = [
        r';\s*DROP\s+TABLE',
        r';\s*DELETE\s+FROM',
        r';\s*UPDATE\s+',
        r'UNION\s+SELECT',
        r'--\s*$',
        r'/\*.*\*/',
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            raise ValidationError(f"Query contains potentially dangerous pattern: {pattern}")
