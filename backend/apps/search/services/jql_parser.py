"""
JQL (Jira Query Language) parser.

Parses JQL queries and converts them to Django QuerySet filters.

Examples:
    project = "PROJ" AND status = "In Progress"
    assignee = currentUser() AND created >= -7d
    type in (Bug, Task) AND priority = High
    text ~ "authentication" AND labels in (security, critical)
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from django.db.models import Q
from django.utils import timezone


class JQLToken:
    """Represents a token in JQL query."""

    def __init__(self, type_: str, value: Any, position: int = 0):
        self.type = type_
        self.value = value
        self.position = position

    def __repr__(self):
        return f"JQLToken({self.type}, {self.value})"


class JQLLexer:
    """
    Lexical analyzer for JQL.

    Converts JQL string into tokens.
    """

    # Token types
    TOKEN_TYPES = {
        'AND': r'\bAND\b',
        'OR': r'\bOR\b',
        'NOT': r'\bNOT\b',
        'IN': r'\bin\b',
        'IS': r'\bis\b',
        'WAS': r'\bwas\b',
        'CHANGED': r'\bCHANGED\b',
        'EMPTY': r'\bEMPTY\b',
        'NULL': r'\bNULL\b',

        # Functions
        'FUNCTION': r'\b(currentUser|now|startOfDay|endOfDay|startOfWeek|endOfWeek|startOfMonth|endOfMonth)\s*\(\)',

        # Operators
        'EQ': r'=',
        'NE': r'!=',
        'LT': r'<',
        'LE': r'<=',
        'GT': r'>',
        'GE': r'>=',
        'CONTAINS': r'~',
        'NOT_CONTAINS': r'!~',

        # Literals
        'STRING': r'"([^"\\\\]|\\\\.)*"',
        'NUMBER': r'-?\d+(\.\d+)?',
        'IDENTIFIER': r'[a-zA-Z_][a-zA-Z0-9_]*',

        # Delimiters
        'LPAREN': r'\(',
        'RPAREN': r'\)',
        'COMMA': r',',

        # Whitespace (ignored)
        'WHITESPACE': r'\s+',
    }

    def __init__(self, query: str):
        self.query = query
        self.position = 0
        self.tokens: List[JQLToken] = []

    def tokenize(self) -> List[JQLToken]:
        """
        Tokenize the JQL query.

        Returns:
            List of JQLToken objects

        Raises:
            ValueError: If query contains invalid syntax
        """
        while self.position < len(self.query):
            match_found = False

            for token_type, pattern in self.TOKEN_TYPES.items():
                regex = re.compile(pattern, re.IGNORECASE)
                match = regex.match(self.query, self.position)

                if match:
                    value = match.group(0)

                    # Skip whitespace
                    if token_type != 'WHITESPACE':
                        # Clean up string literals
                        if token_type == 'STRING':
                            value = value[1:-1]  # Remove quotes
                        # Convert numbers
                        elif token_type == 'NUMBER':
                            value = float(value) if '.' in value else int(value)
                        # Normalize functions
                        elif token_type == 'FUNCTION':
                            value = value.replace('()', '').strip().lower()

                        self.tokens.append(JQLToken(token_type, value, self.position))

                    self.position = match.end()
                    match_found = True
                    break

            if not match_found:
                raise ValueError(
                    f"Invalid JQL syntax at position {self.position}: "
                    f"'{self.query[self.position:self.position + 20]}...'"
                )

        return self.tokens


class JQLParser:
    """
    Parser for JQL queries.

    Converts tokens into Django Q objects.
    """

    # Field mappings from JQL to Django model fields
    FIELD_MAPPINGS = {
        'project': 'project__key',
        'key': 'key',
        'summary': 'summary',
        'description': 'description',
        'type': 'issue_type__name',
        'issuetype': 'issue_type__name',
        'status': 'status__name',
        'priority': 'priority__name',
        'assignee': 'assignee__email',
        'reporter': 'reporter__email',
        'created': 'created_at',
        'updated': 'updated_at',
        'resolved': 'resolved_at',
        'due': 'due_date',
        'labels': 'labels__name',
        'text': None,  # Special handling for full-text search
        'epic': 'epic__key',
        'parent': 'parent__key',
        'sprint': 'sprints__id',
    }

    # Operator mappings
    OPERATOR_MAPPINGS = {
        'EQ': '',
        'NE': '',
        'LT': '__lt',
        'LE': '__lte',
        'GT': '__gt',
        'GE': '__gte',
        'CONTAINS': '__icontains',
        'NOT_CONTAINS': '__icontains',
        'IN': '__in',
    }

    def __init__(self, tokens: List[JQLToken], user=None, organization=None):
        self.tokens = tokens
        self.position = 0
        self.user = user
        self.organization = organization

    def parse(self) -> Q:
        """
        Parse tokens into Django Q object.

        Returns:
            Django Q object representing the query

        Raises:
            ValueError: If query is invalid
        """
        if not self.tokens:
            return Q()

        return self._parse_or_expression()

    def _current_token(self) -> Optional[JQLToken]:
        """Get current token without consuming it."""
        if self.position < len(self.tokens):
            return self.tokens[self.position]
        return None

    def _consume_token(self, expected_type: Optional[str] = None) -> JQLToken:
        """Consume and return current token."""
        token = self._current_token()
        if token is None:
            raise ValueError("Unexpected end of query")

        if expected_type and token.type != expected_type:
            raise ValueError(f"Expected {expected_type}, got {token.type}")

        self.position += 1
        return token

    def _parse_or_expression(self) -> Q:
        """Parse OR expression (lowest precedence)."""
        left = self._parse_and_expression()

        while self._current_token() and self._current_token().type == 'OR':
            self._consume_token('OR')
            right = self._parse_and_expression()
            left = left | right

        return left

    def _parse_and_expression(self) -> Q:
        """Parse AND expression."""
        left = self._parse_not_expression()

        while self._current_token() and self._current_token().type == 'AND':
            self._consume_token('AND')
            right = self._parse_not_expression()
            left = left & right

        return left

    def _parse_not_expression(self) -> Q:
        """Parse NOT expression."""
        if self._current_token() and self._current_token().type == 'NOT':
            self._consume_token('NOT')
            return ~self._parse_primary_expression()

        return self._parse_primary_expression()

    def _parse_primary_expression(self) -> Q:
        """Parse primary expression (field operator value)."""
        token = self._current_token()

        # Handle parentheses
        if token and token.type == 'LPAREN':
            self._consume_token('LPAREN')
            expr = self._parse_or_expression()
            self._consume_token('RPAREN')
            return expr

        # Parse field comparison
        return self._parse_comparison()

    def _parse_comparison(self) -> Q:
        """Parse field comparison (field operator value)."""
        # Get field name
        field_token = self._consume_token('IDENTIFIER')
        field_name = field_token.value.lower()

        # Map to Django field
        django_field = self.FIELD_MAPPINGS.get(field_name)
        if django_field is None and field_name != 'text':
            raise ValueError(f"Unknown field: {field_name}")

        # Get operator
        operator_token = self._current_token()
        if not operator_token:
            raise ValueError(f"Expected operator after field {field_name}")

        # Handle special cases
        if operator_token.type == 'IS':
            return self._parse_is_clause(field_name, django_field)

        if operator_token.type == 'IN':
            return self._parse_in_clause(field_name, django_field)

        if operator_token.type == 'WAS':
            return self._parse_was_clause(field_name, django_field)

        # Standard operators
        if operator_token.type not in self.OPERATOR_MAPPINGS:
            raise ValueError(f"Invalid operator: {operator_token.type}")

        operator = operator_token.type
        self._consume_token()

        # Get value
        value = self._parse_value()

        # Resolve functions
        if isinstance(value, str) and value in ['currentuser', 'now']:
            value = self._resolve_function(value)

        # Build query
        return self._build_query(field_name, django_field, operator, value)

    def _parse_is_clause(self, field_name: str, django_field: Optional[str]) -> Q:
        """Parse IS EMPTY / IS NULL clause."""
        self._consume_token('IS')
        token = self._current_token()

        if not token or token.type not in ('EMPTY', 'NULL'):
            raise ValueError("Expected EMPTY or NULL after IS")

        self._consume_token()

        if django_field:
            return Q(**{f"{django_field}__isnull": True})
        return Q()

    def _parse_in_clause(self, field_name: str, django_field: Optional[str]) -> Q:
        """Parse IN (value1, value2, ...) clause."""
        self._consume_token('IN')
        self._consume_token('LPAREN')

        values = []
        while True:
            value = self._parse_value()
            values.append(value)

            token = self._current_token()
            if not token:
                raise ValueError("Expected ) or , in IN clause")

            if token.type == 'RPAREN':
                self._consume_token('RPAREN')
                break
            elif token.type == 'COMMA':
                self._consume_token('COMMA')
            else:
                raise ValueError(f"Unexpected token in IN clause: {token.type}")

        if django_field:
            return Q(**{f"{django_field}__in": values})
        return Q()

    def _parse_was_clause(self, field_name: str, django_field: Optional[str]) -> Q:
        """Parse WAS clause (historical data - simplified implementation)."""
        self._consume_token('WAS')

        # For now, treat WAS the same as current value
        # In production, this would query issue history
        token = self._current_token()

        if token and token.type in ('EMPTY', 'NULL'):
            self._consume_token()
            if django_field:
                return Q(**{f"{django_field}__isnull": True})
        else:
            value = self._parse_value()
            if django_field:
                return Q(**{django_field: value})

        return Q()

    def _parse_value(self) -> Any:
        """Parse a value (string, number, function)."""
        token = self._current_token()
        if not token:
            raise ValueError("Expected value")

        if token.type in ('STRING', 'NUMBER', 'IDENTIFIER'):
            value = token.value
            self._consume_token()
            return value
        elif token.type == 'FUNCTION':
            func_name = token.value
            self._consume_token()
            return func_name
        else:
            raise ValueError(f"Unexpected token as value: {token.type}")

    def _resolve_function(self, func_name: str) -> Any:
        """Resolve JQL function to actual value."""
        func_name = func_name.lower()

        if func_name == 'currentuser':
            if self.user:
                return self.user.email
            return None

        elif func_name == 'now':
            return timezone.now()

        elif func_name == 'startofday':
            now = timezone.now()
            return now.replace(hour=0, minute=0, second=0, microsecond=0)

        elif func_name == 'endofday':
            now = timezone.now()
            return now.replace(hour=23, minute=59, second=59, microsecond=999999)

        elif func_name == 'startofweek':
            now = timezone.now()
            start = now - timedelta(days=now.weekday())
            return start.replace(hour=0, minute=0, second=0, microsecond=0)

        elif func_name == 'endofweek':
            now = timezone.now()
            end = now + timedelta(days=6 - now.weekday())
            return end.replace(hour=23, minute=59, second=59, microsecond=999999)

        elif func_name == 'startofmonth':
            now = timezone.now()
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        elif func_name == 'endofmonth':
            now = timezone.now()
            if now.month == 12:
                next_month = now.replace(year=now.year + 1, month=1, day=1)
            else:
                next_month = now.replace(month=now.month + 1, day=1)
            last_day = next_month - timedelta(days=1)
            return last_day.replace(hour=23, minute=59, second=59, microsecond=999999)

        return None

    def _build_query(self, field_name: str, django_field: Optional[str], operator: str, value: Any) -> Q:
        """Build Django Q object for a field comparison."""
        # Handle special full-text search
        if field_name == 'text':
            # Full-text search across multiple fields
            q = Q()
            q |= Q(summary__icontains=value)
            q |= Q(description__icontains=value)
            q |= Q(key__icontains=value)
            return q

        if not django_field:
            return Q()

        # Build lookup
        lookup_suffix = self.OPERATOR_MAPPINGS.get(operator, '')
        lookup = f"{django_field}{lookup_suffix}"

        # Handle date relative values (e.g., "-7d", "+1w")
        if isinstance(value, str) and re.match(r'^[+-]\d+[dwmy]$', value):
            value = self._parse_relative_date(value)

        # Build query
        if operator == 'NE' or operator == 'NOT_CONTAINS':
            return ~Q(**{lookup: value})
        else:
            return Q(**{lookup: value})

    def _parse_relative_date(self, value: str) -> datetime:
        """
        Parse relative date strings.

        Examples:
            -7d -> 7 days ago
            +1w -> 1 week from now
            -1m -> 1 month ago
            -1y -> 1 year ago
        """
        match = re.match(r'^([+-])(\d+)([dwmy])$', value)
        if not match:
            return value

        sign, amount, unit = match.groups()
        amount = int(amount)
        if sign == '-':
            amount = -amount

        now = timezone.now()

        if unit == 'd':
            return now + timedelta(days=amount)
        elif unit == 'w':
            return now + timedelta(weeks=amount)
        elif unit == 'm':
            # Approximate month as 30 days
            return now + timedelta(days=amount * 30)
        elif unit == 'y':
            # Approximate year as 365 days
            return now + timedelta(days=amount * 365)

        return now


class JQLService:
    """Service for parsing and executing JQL queries."""

    @staticmethod
    def parse_jql(query: str, user=None, organization=None) -> Q:
        """
        Parse JQL query string into Django Q object.

        Args:
            query: JQL query string
            user: Current user for functions like currentUser()
            organization: Current organization for scoping

        Returns:
            Django Q object representing the query

        Raises:
            ValueError: If query is invalid

        Examples:
            >>> parse_jql('project = "PROJ" AND status = "Open"')
            >>> parse_jql('assignee = currentUser() AND created >= -7d')
        """
        try:
            # Tokenize
            lexer = JQLLexer(query)
            tokens = lexer.tokenize()

            # Parse
            parser = JQLParser(tokens, user=user, organization=organization)
            return parser.parse()

        except Exception as e:
            raise ValueError(f"Invalid JQL query: {str(e)}")

    @staticmethod
    def validate_jql(query: str) -> Tuple[bool, Optional[str]]:
        """
        Validate JQL query syntax.

        Args:
            query: JQL query string

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            JQLService.parse_jql(query)
            return True, None
        except Exception as e:
            return False, str(e)
