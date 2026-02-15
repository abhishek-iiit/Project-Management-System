"""
drf-spectacular configuration for OpenAPI schema generation.
"""

SPECTACULAR_SETTINGS = {
    'TITLE': 'BugsTracker API',
    'DESCRIPTION': '''
# BugsTracker API Documentation

A production-grade Jira-equivalent project management and issue tracking system.

## Features

- **Multi-tenant Architecture**: Organization-based isolation
- **Dynamic Workflows**: Configurable state machines with transitions
- **Issue Tracking**: Full-featured issue management with custom fields
- **Agile Boards**: Scrum and Kanban boards with sprint management
- **Automation Engine**: Rule-based automation with triggers and actions
- **Advanced Search**: JQL (Jira Query Language) support
- **Real-time Updates**: WebSocket-based notifications
- **Webhooks**: Event-driven integrations
- **Audit Logging**: Comprehensive activity tracking

## Authentication

All API endpoints (except registration and login) require JWT authentication.

**Obtaining a token:**

```bash
POST /api/v1/auth/login/
{
  "email": "user@example.com",
  "password": "password"
}

Response:
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Using the token:**

Include the access token in the Authorization header:

```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Refreshing the token:**

```bash
POST /api/v1/auth/refresh/
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

## Rate Limiting

- **Authenticated users**: 1000 requests/hour
- **Anonymous users**: 100 requests/hour
- **Burst limit**: 20 requests/minute

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Maximum requests per hour
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Time when the limit resets (Unix timestamp)

## Pagination

All list endpoints support pagination:

**Query Parameters:**
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 50, max: 100)

**Response:**
```json
{
  "count": 100,
  "next": "http://api.example.com/resource/?page=3",
  "previous": "http://api.example.com/resource/?page=1",
  "results": [...]
}
```

## Filtering and Search

Many endpoints support filtering via query parameters:

```bash
# Filter issues by status
GET /api/v1/issues/?status=in-progress

# Filter by multiple values
GET /api/v1/issues/?priority=high&priority=critical

# Search
GET /api/v1/issues/?search=authentication

# JQL search
GET /api/v1/search/?jql=project=PROJ AND assignee=currentUser()
```

## Field Selection

Use `fields` parameter to retrieve specific fields only:

```bash
GET /api/v1/issues/?fields=id,key,summary,status
```

## Ordering

Use `ordering` parameter to sort results:

```bash
# Ascending
GET /api/v1/issues/?ordering=created_at

# Descending
GET /api/v1/issues/?ordering=-created_at

# Multiple fields
GET /api/v1/issues/?ordering=-priority,created_at
```

## Error Handling

All errors follow a consistent format:

```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "email": ["This field is required."]
    }
  }
}
```

**Common Error Codes:**
- `AUTHENTICATION_ERROR`: Missing or invalid authentication
- `PERMISSION_DENIED`: Insufficient permissions
- `VALIDATION_ERROR`: Invalid input data
- `NOT_FOUND`: Resource not found
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `SERVER_ERROR`: Internal server error

## Versioning

The API uses URL path versioning:

- **Current version**: v1 (`/api/v1/`)
- **Future versions**: v2 (`/api/v2/`)

Deprecated endpoints will include a `Deprecation` header with sunset date.

## WebSocket Connections

Real-time updates are available via WebSocket:

```javascript
// Notifications
const ws = new WebSocket('ws://api.example.com/ws/notifications/');

// Issue updates
const ws = new WebSocket('ws://api.example.com/ws/issues/{issue_id}/');
```

Authentication via query parameter:
```
ws://api.example.com/ws/notifications/?token=<access_token>
```

## Changelog

### v1.0.0 (2026-02-15)
- Initial release
- Complete issue tracking system
- Agile boards and sprints
- Workflow engine
- Automation rules
- Search with JQL
- Real-time notifications
- Webhooks
- Audit logging
    ''',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'CONTACT': {
        'name': 'BugsTracker Support',
        'email': 'support@bugstracker.com',
    },
    'LICENSE': {
        'name': 'Proprietary',
    },

    # Security schemes
    'SECURITY': [
        {
            'BearerAuth': []
        }
    ],
    'APPEND_COMPONENTS': {
        'securitySchemes': {
            'BearerAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
                'description': 'JWT access token obtained from /api/v1/auth/login/',
            }
        }
    },

    # Schema generation settings
    'COMPONENT_SPLIT_REQUEST': True,
    'COMPONENT_NO_READ_ONLY_REQUIRED': True,

    # API versioning
    'SERVERS': [
        {
            'url': 'http://localhost:8000',
            'description': 'Development server',
        },
        {
            'url': 'https://api.bugstracker.com',
            'description': 'Production server',
        },
        {
            'url': 'https://staging-api.bugstracker.com',
            'description': 'Staging server',
        },
    ],

    # Operation ID generation
    'CAMELIZE_NAMES': True,
    'SCHEMA_PATH_PREFIX': '/api/v[0-9]',
    'SCHEMA_PATH_PREFIX_TRIM': True,

    # Tags for endpoint grouping
    'TAGS': [
        {
            'name': 'Authentication',
            'description': 'User authentication and token management',
        },
        {
            'name': 'Organizations',
            'description': 'Multi-tenant organization management',
        },
        {
            'name': 'Projects',
            'description': 'Project creation and configuration',
        },
        {
            'name': 'Issues',
            'description': 'Issue tracking and management',
        },
        {
            'name': 'Workflows',
            'description': 'Workflow and transition management',
        },
        {
            'name': 'Fields',
            'description': 'Custom field configuration',
        },
        {
            'name': 'Boards',
            'description': 'Agile boards (Scrum/Kanban)',
        },
        {
            'name': 'Sprints',
            'description': 'Sprint management and planning',
        },
        {
            'name': 'Automation',
            'description': 'Automation rules and execution',
        },
        {
            'name': 'Search',
            'description': 'Search and JQL queries',
        },
        {
            'name': 'Notifications',
            'description': 'Notification preferences and history',
        },
        {
            'name': 'Webhooks',
            'description': 'Webhook subscriptions and deliveries',
        },
        {
            'name': 'Audit',
            'description': 'Audit logs and activity tracking',
        },
    ],

    # Response customization
    'POSTPROCESSING_HOOKS': [
        'drf_spectacular.hooks.postprocess_schema_enums',
    ],

    # Extensions
    'EXTENSIONS_INFO': {
        'x-api-id': 'bugstracker-api',
    },

    # Enum handling
    'ENUM_NAME_OVERRIDES': {
        # 'IssueStatusEnum': 'apps.issues.models.IssueStatus',
        # 'IssuePriorityEnum': 'apps.issues.models.IssuePriority',
        # 'IssueTypeEnum': 'apps.issues.models.IssueType',
        'WorkflowStatusCategoryEnum': 'apps.workflows.models.StatusCategory',
        'AutomationTriggerTypeEnum': 'apps.automation.models.TriggerType',
        'AuditActionEnum': 'apps.audit.models.AuditAction',
    },

    # Custom schema preprocessing
    'PREPROCESSING_HOOKS': [],

    # Swagger UI settings
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
        'defaultModelsExpandDepth': 2,
        'defaultModelExpandDepth': 2,
        'displayRequestDuration': True,
        'docExpansion': 'none',
        'filter': True,
        'operationsSorter': 'alpha',
        'showExtensions': True,
        'tagsSorter': 'alpha',
        'tryItOutEnabled': True,
    },

    # ReDoc settings
    'REDOC_UI_SETTINGS': {
        'hideDownloadButton': False,
        'expandResponses': '200,201',
        'pathInMiddlePanel': True,
        'nativeScrollbars': True,
        'theme': {
            'colors': {
                'primary': {
                    'main': '#2196F3'
                }
            },
            'typography': {
                'fontSize': '14px',
                'headings': {
                    'fontFamily': 'Roboto, sans-serif'
                }
            }
        }
    },

    # Sorting
    'SORT_OPERATION_PARAMETERS': True,
    'SORT_OPERATIONS': False,
}
