"""
Input sanitization utilities to prevent XSS and injection attacks.
"""

import bleach
import re
from typing import Optional, List
from django.utils.html import escape


# Allowed HTML tags for rich text fields (comments, descriptions)
ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'blockquote', 'code', 'pre', 'hr', 'ul', 'ol', 'li', 'a', 'img',
    'table', 'thead', 'tbody', 'tr', 'th', 'td'
]

# Allowed HTML attributes
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target', 'rel'],
    'img': ['src', 'alt', 'title', 'width', 'height'],
    'code': ['class'],
    'pre': ['class'],
    'td': ['colspan', 'rowspan'],
    'th': ['colspan', 'rowspan'],
}

# Allowed protocols for links
ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']


def sanitize_html(
    html: str,
    allowed_tags: Optional[List[str]] = None,
    allowed_attributes: Optional[dict] = None,
    strip: bool = True
) -> str:
    """
    Sanitize HTML content to prevent XSS attacks.

    Args:
        html: HTML string to sanitize
        allowed_tags: List of allowed HTML tags (default: ALLOWED_TAGS)
        allowed_attributes: Dict of allowed attributes per tag (default: ALLOWED_ATTRIBUTES)
        strip: Whether to strip disallowed tags (True) or escape them (False)

    Returns:
        Sanitized HTML string

    Examples:
        >>> sanitize_html('<script>alert("XSS")</script><p>Safe content</p>')
        '<p>Safe content</p>'

        >>> sanitize_html('<a href="javascript:alert()">Link</a>')
        '<a>Link</a>'
    """
    if not html:
        return ""

    tags = allowed_tags or ALLOWED_TAGS
    attributes = allowed_attributes or ALLOWED_ATTRIBUTES

    # Clean HTML using bleach
    cleaned = bleach.clean(
        html,
        tags=tags,
        attributes=attributes,
        protocols=ALLOWED_PROTOCOLS,
        strip=strip
    )

    # Additional sanitization: remove potentially dangerous attributes
    cleaned = re.sub(r'on\w+\s*=', '', cleaned)  # Remove event handlers
    cleaned = re.sub(r'javascript:', '', cleaned, flags=re.IGNORECASE)  # Remove javascript: protocol

    return cleaned


def sanitize_input(
    value: str,
    max_length: Optional[int] = None,
    allow_html: bool = False
) -> str:
    """
    Sanitize user input for storage and display.

    Args:
        value: Input string to sanitize
        max_length: Maximum allowed length (truncate if longer)
        allow_html: Whether to allow HTML tags (will be sanitized)

    Returns:
        Sanitized string

    Examples:
        >>> sanitize_input('<script>alert("XSS")</script>')
        '&lt;script&gt;alert(&quot;XSS&quot;)&lt;/script&gt;'

        >>> sanitize_input('<p>Text</p>', allow_html=True)
        '<p>Text</p>'
    """
    if not value:
        return ""

    # Truncate if needed
    if max_length and len(value) > max_length:
        value = value[:max_length]

    # Remove null bytes
    value = value.replace('\x00', '')

    # Strip leading/trailing whitespace
    value = value.strip()

    # Sanitize based on HTML allowance
    if allow_html:
        return sanitize_html(value)
    else:
        # Escape HTML entities
        return escape(value)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent directory traversal and other attacks.

    Args:
        filename: Original filename

    Returns:
        Safe filename

    Examples:
        >>> sanitize_filename('../../etc/passwd')
        'etc_passwd'

        >>> sanitize_filename('file<script>.txt')
        'file_script_.txt'
    """
    if not filename:
        return "unnamed_file"

    # Remove directory traversal attempts
    filename = filename.replace('..', '')
    filename = filename.replace('/', '_')
    filename = filename.replace('\\', '_')

    # Remove special characters
    filename = re.sub(r'[^\w\s\-\.]', '_', filename)

    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')

    # Ensure filename is not empty
    if not filename:
        return "unnamed_file"

    return filename


def sanitize_sql_identifier(identifier: str) -> str:
    """
    Sanitize SQL identifier (table name, column name).

    WARNING: Always use Django ORM parameterized queries.
    This is only for edge cases where identifiers come from user input.

    Args:
        identifier: SQL identifier to sanitize

    Returns:
        Safe identifier

    Examples:
        >>> sanitize_sql_identifier('users; DROP TABLE users;')
        'users_DROP_TABLE_users'
    """
    # Only allow alphanumeric and underscores
    identifier = re.sub(r'[^\w]', '_', identifier)

    # Ensure doesn't start with number
    if identifier and identifier[0].isdigit():
        identifier = f"_{identifier}"

    return identifier


def remove_unicode_control_chars(text: str) -> str:
    """
    Remove Unicode control characters that could be used for attacks.

    Args:
        text: Input text

    Returns:
        Text without control characters
    """
    if not text:
        return ""

    # Remove control characters except newline, carriage return, and tab
    return "".join(
        char for char in text
        if char in ('\n', '\r', '\t') or not (ord(char) < 32 or ord(char) == 127)
    )


def sanitize_jql_query(query: str) -> str:
    """
    Sanitize JQL (Jira Query Language) query to prevent injection.

    Args:
        query: JQL query string

    Returns:
        Sanitized query

    Note:
        This is a basic sanitization. Full JQL parser validation
        should be done in the search service layer.
    """
    if not query:
        return ""

    # Remove null bytes
    query = query.replace('\x00', '')

    # Remove SQL-like comments
    query = re.sub(r'--.*', '', query)
    query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)

    # Remove control characters
    query = remove_unicode_control_chars(query)

    return query.strip()
