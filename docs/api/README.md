# BugsTracker API Documentation

Production-grade Jira-equivalent issue tracking and project management system.

## Table of Contents

- [Getting Started](#getting-started)
- [Authentication](#authentication)
- [API Endpoints](#api-endpoints)
- [Rate Limiting](#rate-limiting)
- [Pagination](#pagination)
- [Filtering & Search](#filtering--search)
- [Error Handling](#error-handling)
- [Versioning](#versioning)
- [WebSocket Connections](#websocket-connections)
- [Examples](#examples)

## Getting Started

### Base URL

- **Development**: `http://localhost:8000/api/v1`
- **Staging**: `https://staging-api.bugstracker.com/api/v1`
- **Production**: `https://api.bugstracker.com/api/v1`

### API Documentation UI

- **Swagger UI**: `/api/docs/`
- **ReDoc**: `/api/redoc/`
- **OpenAPI Schema**: `/api/schema/`

### Quick Start

1. **Register a new user**:
   ```bash
   POST /api/v1/auth/register/
   {
     "email": "user@example.com",
     "password": "SecurePassword123!",
     "full_name": "John Doe"
   }
   ```

2. **Login to get access token**:
   ```bash
   POST /api/v1/auth/login/
   {
     "email": "user@example.com",
     "password": "SecurePassword123!"
   }

   Response:
   {
     "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
     "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
   }
   ```

3. **Use the access token** in subsequent requests:
   ```bash
   Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
   ```

## Authentication

All API endpoints (except registration and login) require JWT authentication.

### Obtaining Tokens

**Login**:
```http
POST /api/v1/auth/login/
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password"
}
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user@example.com",
      "full_name": "John Doe"
    }
  }
}
```

### Using Access Token

Include the access token in the `Authorization` header:

```http
GET /api/v1/issues/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

### Refreshing Token

Access tokens expire after 60 minutes (configurable). Use the refresh token to obtain a new access token:

```http
POST /api/v1/auth/refresh/
Content-Type: application/json

{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response**:
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."  // New refresh token
}
```

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register/` | Register new user |
| POST | `/auth/login/` | Login and get tokens |
| POST | `/auth/refresh/` | Refresh access token |
| POST | `/auth/logout/` | Logout (blacklist token) |
| GET | `/auth/me/` | Get current user profile |

### Organizations

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/organizations/` | Create organization |
| GET | `/organizations/` | List user's organizations |
| GET | `/organizations/{id}/` | Get organization details |
| PUT | `/organizations/{id}/` | Update organization |
| DELETE | `/organizations/{id}/` | Delete organization |
| POST | `/organizations/{id}/members/` | Add member to organization |
| GET | `/organizations/{id}/members/` | List organization members |
| DELETE | `/organizations/{id}/members/{user_id}/` | Remove member |

### Projects

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/projects/` | Create project |
| GET | `/projects/` | List projects |
| GET | `/projects/{id}/` | Get project details |
| PUT | `/projects/{id}/` | Update project |
| DELETE | `/projects/{id}/` | Delete project |
| POST | `/projects/{id}/members/` | Add project member |
| GET | `/projects/{id}/members/` | List project members |

### Issues

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/issues/` | Create issue |
| GET | `/issues/` | List issues |
| GET | `/issues/{id}/` | Get issue details |
| PUT | `/issues/{id}/` | Update issue |
| DELETE | `/issues/{id}/` | Delete issue |
| POST | `/issues/{id}/transition/` | Transition issue status |
| POST | `/issues/{id}/comments/` | Add comment |
| GET | `/issues/{id}/comments/` | List comments |
| POST | `/issues/{id}/attachments/` | Upload attachment |
| POST | `/issues/{id}/watchers/` | Add watcher |
| GET | `/issues/{id}/history/` | Get issue history |

### Workflows

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/workflows/` | Create workflow |
| GET | `/workflows/` | List workflows |
| GET | `/workflows/{id}/` | Get workflow details |
| PUT | `/workflows/{id}/` | Update workflow |
| POST | `/workflows/{id}/transitions/` | Add transition |
| GET | `/workflows/{id}/transitions/` | List transitions |

### Boards & Sprints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/boards/` | Create board |
| GET | `/boards/` | List boards |
| GET | `/boards/{id}/` | Get board details |
| GET | `/boards/{id}/issues/` | Get board issues |
| POST | `/boards/{id}/sprints/` | Create sprint |
| POST | `/sprints/{id}/start/` | Start sprint |
| POST | `/sprints/{id}/complete/` | Complete sprint |

### Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/search/?jql=...` | JQL search |
| POST | `/search/filters/` | Save filter |
| GET | `/search/filters/` | List saved filters |

### Automation

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/automation/rules/` | Create automation rule |
| GET | `/automation/rules/` | List automation rules |
| PUT | `/automation/rules/{id}/` | Update rule |
| DELETE | `/automation/rules/{id}/` | Delete rule |

### Webhooks

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/webhooks/` | Create webhook |
| GET | `/webhooks/` | List webhooks |
| DELETE | `/webhooks/{id}/` | Delete webhook |
| GET | `/webhooks/{id}/deliveries/` | View webhook deliveries |

### Notifications

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/notifications/` | List notifications |
| PUT | `/notifications/{id}/read/` | Mark as read |
| GET | `/notifications/preferences/` | Get preferences |
| PUT | `/notifications/preferences/` | Update preferences |

### Audit Logs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/audit-logs/` | List audit logs |
| GET | `/audit-logs/{id}/` | Get audit log details |
| GET | `/audit-logs/entity/{type}/{id}/` | Get entity history |
| GET | `/audit-logs/statistics/` | Get audit statistics |
| POST | `/audit-logs/export/` | Export to CSV |

## Rate Limiting

Rate limits protect the API from abuse and ensure fair usage.

### Limits

- **Authenticated users**: 1,000 requests per hour
- **Anonymous users**: 100 requests per hour
- **Burst limit**: 20 requests per minute

### Rate Limit Headers

Every response includes rate limit information:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 998
X-RateLimit-Reset: 1708002000
```

### Exceeding Limits

When rate limit is exceeded, API returns `429 Too Many Requests`:

```json
{
  "status": "error",
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Try again in 3600 seconds.",
    "retry_after": 3600
  }
}
```

Response includes `Retry-After` header with seconds to wait.

## Pagination

All list endpoints support pagination.

### Query Parameters

- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 50, max: 100)

### Example Request

```http
GET /api/v1/issues/?page=2&page_size=25
```

### Response Format

```json
{
  "count": 100,
  "next": "http://api.example.com/api/v1/issues/?page=3",
  "previous": "http://api.example.com/api/v1/issues/?page=1",
  "results": [
    {
      "id": "...",
      "key": "PROJ-123",
      "summary": "..."
    }
  ]
}
```

## Filtering & Search

### Query Parameters

- `search`: Full-text search
- `ordering`: Sort by field (prefix with `-` for descending)
- `fields`: Comma-separated list of fields to include

### Examples

**Filter by field**:
```http
GET /api/v1/issues/?status=in-progress&priority=high
```

**Full-text search**:
```http
GET /api/v1/issues/?search=authentication
```

**Ordering**:
```http
GET /api/v1/issues/?ordering=-created_at,priority
```

**Field selection**:
```http
GET /api/v1/issues/?fields=id,key,summary,status
```

### JQL (Jira Query Language)

Advanced queries using JQL:

```http
GET /api/v1/search/?jql=project="PROJ" AND status="in_progress" AND assignee=currentUser()
```

**Supported operators**: `=`, `!=`, `>`, `<`, `>=`, `<=`, `IN`, `NOT IN`, `~`, `!~`

**Supported functions**: `currentUser()`, `openSprints()`, `closedSprints()`

## Error Handling

All errors follow a consistent format:

```json
{
  "status": "error",
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {}
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Invalid input data |
| `AUTHENTICATION_ERROR` | 401 | Missing or invalid authentication |
| `PERMISSION_DENIED` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `SERVER_ERROR` | 500 | Internal server error |

### Example Error Response

```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "email": ["This field is required."],
      "password": ["This field must be at least 8 characters."]
    }
  }
}
```

## Versioning

The API uses URL path versioning:

- **Current version**: `v1` (`/api/v1/`)
- **Future versions**: `v2` (`/api/v2/`)

### Version Headers

Responses include the API version:

```http
X-API-Version: v1
```

### Deprecation

Deprecated endpoints include deprecation headers:

```http
Deprecation: true
Sunset: 2026-12-31
Link: </api/v2/>; rel="successor-version"
Warning: 299 - "API version v1 is deprecated..."
```

## WebSocket Connections

Real-time updates via WebSocket.

### Notifications

```javascript
const ws = new WebSocket('ws://api.example.com/ws/notifications/?token=<access_token>');

ws.onmessage = (event) => {
  const notification = JSON.parse(event.data);
  console.log('New notification:', notification);
};
```

### Issue Updates

```javascript
const ws = new WebSocket('ws://api.example.com/ws/issues/{issue_id}/?token=<access_token>');

ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log('Issue updated:', update);
};
```

## Examples

### Complete Workflow Example

```bash
# 1. Register
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecurePassword123!", "full_name": "John Doe"}'

# 2. Login
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecurePassword123!"}' \
  | jq -r '.data.access')

# 3. Create Organization
ORG_ID=$(curl -X POST http://localhost:8000/api/v1/organizations/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Company", "slug": "my-company"}' \
  | jq -r '.data.id')

# 4. Create Project
PROJECT_ID=$(curl -X POST http://localhost:8000/api/v1/projects/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"organization\": \"$ORG_ID\", \"name\": \"My Project\", \"key\": \"PROJ\"}" \
  | jq -r '.data.id')

# 5. Create Issue
ISSUE_ID=$(curl -X POST http://localhost:8000/api/v1/issues/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"project\": \"$PROJECT_ID\", \"summary\": \"First issue\", \"issue_type\": \"task\"}" \
  | jq -r '.data.id')

# 6. Get Issue
curl -X GET "http://localhost:8000/api/v1/issues/$ISSUE_ID/" \
  -H "Authorization: Bearer $TOKEN"
```

### Python Example

```python
import requests

# Base URL
BASE_URL = "http://localhost:8000/api/v1"

# Login
response = requests.post(f"{BASE_URL}/auth/login/", json={
    "email": "user@example.com",
    "password": "SecurePassword123!"
})
token = response.json()['data']['access']

# Headers for authenticated requests
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# List issues
response = requests.get(f"{BASE_URL}/issues/", headers=headers)
issues = response.json()['results']

for issue in issues:
    print(f"{issue['key']}: {issue['summary']}")

# Create issue
new_issue = requests.post(f"{BASE_URL}/issues/", headers=headers, json={
    "project": "550e8400-e29b-41d4-a716-446655440000",
    "summary": "New bug found",
    "issue_type": "bug",
    "priority": "high"
})
print(f"Created: {new_issue.json()['data']['key']}")
```

## Support

- **Documentation**: `/api/docs/`
- **Issues**: https://github.com/bugstracker/bugstracker/issues
- **Email**: support@bugstracker.com

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
