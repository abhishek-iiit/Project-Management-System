# API Changelog

All notable changes to the BugsTracker API will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- GraphQL API endpoint
- Bulk operations API
- Batch request support
- API webhook retry configuration UI
- Custom field type: Rich Text Editor
- Advanced JQL functions (e.g., `nearestWorkDay()`, `businessDays()`)

---

## [1.0.0] - 2026-02-15

### Added

#### Authentication & Authorization
- JWT-based authentication with access and refresh tokens
- User registration and login endpoints
- Token refresh endpoint
- Logout endpoint (token blacklisting)
- Current user profile endpoint
- Role-based access control (RBAC)
- Object-level permissions
- Multi-tenant organization support

#### Organizations
- Create, read, update, delete organizations
- Organization member management
- Organization-based data isolation
- Organization roles and permissions

#### Projects
- Create, read, update, delete projects
- Project member management
- Project roles (Admin, Developer, Viewer)
- Project configuration and settings
- Project templates

#### Issues
- Create, read, update, delete issues
- Dynamic custom fields (JSONB)
- Issue types (Epic, Story, Task, Bug, Subtask)
- Issue priorities (Blocker, High, Medium, Low)
- Issue hierarchy (Epic > Story > Task > Subtask)
- Issue linking (blocks, relates to, duplicates)
- Issue comments with mentions
- File attachments support
- Issue watchers
- Issue history tracking
- Issue key generation (PROJECT-123)

#### Workflows
- Workflow creation and management
- Status management with categories
- Transition definitions with conditions
- Workflow validators
- Post-functions on transitions
- Workflow schemes (project-specific)
- State machine execution

#### Custom Fields
- Field definition management
- Field types: text, number, date, select, multi-select, user, checkbox, URL, labels
- Field validation rules
- Context-specific fields (project/issue type)
- Field configuration (required, default, options)

#### Agile Boards
- Scrum and Kanban board support
- Board creation and configuration
- Column configuration (status mapping)
- Swimlane configuration (by assignee, priority, epic)
- Quick filters
- Backlog management
- Issue ranking (drag & drop order)

#### Sprints
- Sprint creation and management
- Sprint start/end dates and goals
- Sprint activation and completion
- Sprint reports (burndown, velocity)
- Issue-sprint associations

#### Automation
- Automation rule creation
- Trigger types: issue created, updated, transitioned, field changed, scheduled
- Condition types: field equals, user in role, issue type, JQL match
- Action types: update field, assign user, transition, comment, notify, create linked issue, webhook
- Smart values ({{issue.key}}, {{assignee.email}})
- Async execution via Celery
- Execution audit trail

#### Search & JQL
- Full-text search
- JQL (Jira Query Language) support
- Saved filters
- Filter sharing and permissions
- Elasticsearch integration (placeholder)
- Search autocomplete
- Advanced faceting

#### Notifications
- In-app notifications
- Real-time WebSocket notifications
- Email notifications
- Notification preferences
- Mention detection (@username)
- Notification batching

#### Webhooks
- Webhook creation and management
- Event subscriptions
- HMAC signature generation (SHA-256)
- Async delivery with Celery
- Exponential backoff retry (60s, 120s, 240s)
- Delivery audit trail
- Webhook testing endpoint

#### Audit Logging
- Comprehensive audit trail
- Field-level change tracking
- IP address and user agent capture
- Request metadata tracking
- Immutable audit logs
- Entity history endpoint
- Audit statistics
- CSV export

#### API Documentation
- OpenAPI 3.0 schema
- Swagger UI interactive documentation
- ReDoc alternative documentation
- Request/response examples
- Authentication documentation
- Rate limit documentation
- Error code documentation
- Postman collection

#### API Features
- RESTful API design
- JWT authentication
- Pagination (cursor-based)
- Filtering and search
- Field selection
- Ordering/sorting
- Rate limiting (1000 req/hour authenticated, 100 req/hour anonymous)
- Rate limit headers
- CORS support
- Versioning (URL path: /api/v1/)
- Health check endpoint
- Request ID tracking
- Server time headers

### API Endpoints

**Authentication** (`/auth/`)
- `POST /register/` - Register new user
- `POST /login/` - Login and get tokens
- `POST /refresh/` - Refresh access token
- `POST /logout/` - Logout
- `GET /me/` - Get current user

**Organizations** (`/organizations/`)
- `POST /` - Create organization
- `GET /` - List organizations
- `GET /{id}/` - Get organization
- `PUT /{id}/` - Update organization
- `DELETE /{id}/` - Delete organization
- `POST /{id}/members/` - Add member
- `GET /{id}/members/` - List members
- `DELETE /{id}/members/{user_id}/` - Remove member

**Projects** (`/projects/`)
- `POST /` - Create project
- `GET /` - List projects
- `GET /{id}/` - Get project
- `PUT /{id}/` - Update project
- `DELETE /{id}/` - Delete project
- `POST /{id}/members/` - Add member
- `GET /{id}/members/` - List members

**Issues** (`/issues/`)
- `POST /` - Create issue
- `GET /` - List issues
- `GET /{id}/` - Get issue
- `PUT /{id}/` - Update issue
- `DELETE /{id}/` - Delete issue
- `POST /{id}/transition/` - Transition status
- `POST /{id}/comments/` - Add comment
- `GET /{id}/comments/` - List comments
- `POST /{id}/attachments/` - Upload attachment
- `POST /{id}/watchers/` - Add watcher
- `GET /{id}/history/` - Get history

**Workflows** (`/workflows/`)
- `POST /` - Create workflow
- `GET /` - List workflows
- `GET /{id}/` - Get workflow
- `PUT /{id}/` - Update workflow
- `POST /{id}/transitions/` - Add transition
- `GET /{id}/transitions/` - List transitions

**Fields** (`/fields/`)
- `POST /` - Create field
- `GET /` - List fields
- `GET /{id}/` - Get field
- `PUT /{id}/` - Update field
- `DELETE /{id}/` - Delete field

**Boards** (`/boards/`)
- `POST /` - Create board
- `GET /` - List boards
- `GET /{id}/` - Get board
- `GET /{id}/issues/` - Get board issues
- `POST /{id}/sprints/` - Create sprint
- `PUT /{id}/issues/rank/` - Rank issues

**Sprints** (`/sprints/`)
- `POST /{id}/start/` - Start sprint
- `POST /{id}/complete/` - Complete sprint

**Automation** (`/automation/rules/`)
- `POST /` - Create rule
- `GET /` - List rules
- `PUT /{id}/` - Update rule
- `DELETE /{id}/` - Delete rule

**Search** (`/search/`)
- `GET /?jql=...` - JQL search
- `POST /filters/` - Save filter
- `GET /filters/` - List filters
- `GET /autocomplete/?q=...` - Autocomplete

**Notifications** (`/notifications/`)
- `GET /` - List notifications
- `PUT /{id}/read/` - Mark as read
- `PUT /mark-all-read/` - Mark all as read
- `GET /preferences/` - Get preferences
- `PUT /preferences/` - Update preferences

**Webhooks** (`/webhooks/`)
- `POST /` - Create webhook
- `GET /` - List webhooks
- `DELETE /{id}/` - Delete webhook
- `POST /{id}/test/` - Test webhook
- `GET /{id}/deliveries/` - Get deliveries

**Audit Logs** (`/audit-logs/`)
- `GET /` - List audit logs
- `GET /{id}/` - Get audit log
- `GET /entity/{type}/{id}/` - Get entity history
- `GET /statistics/` - Get statistics
- `POST /export/` - Export to CSV

**WebSocket**
- `/ws/notifications/` - Real-time notifications
- `/ws/issues/{id}/` - Real-time issue updates

### Response Format

**Success Response:**
```json
{
  "status": "success",
  "data": {...},
  "message": "Operation completed successfully"
}
```

**Error Response:**
```json
{
  "status": "error",
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": {}
  }
}
```

### Rate Limits
- Authenticated: 1000 requests/hour
- Anonymous: 100 requests/hour
- Burst: 20 requests/minute

### Headers

**Request Headers:**
- `Authorization: Bearer <token>` - JWT authentication
- `Content-Type: application/json` - Request content type
- `X-Organization-ID: <uuid>` - Optional organization context

**Response Headers:**
- `X-API-Version: v1` - API version
- `X-Request-ID: <uuid>` - Request tracking ID
- `X-RateLimit-Limit: 1000` - Rate limit maximum
- `X-RateLimit-Remaining: 998` - Remaining requests
- `X-RateLimit-Reset: 1708002000` - Reset timestamp
- `X-Server-Time: 2026-02-15T10:30:00.000Z` - Server timestamp

### Breaking Changes
None (initial release)

### Deprecated
None (initial release)

### Security
- JWT token expiration: 60 minutes (configurable)
- Refresh token rotation enabled
- Token blacklisting on logout
- HTTPS required in production
- CORS configured
- CSRF protection enabled
- Rate limiting active
- Input validation on all endpoints
- SQL injection prevention
- XSS prevention

---

## Future Versions

### [2.0.0] - TBD

#### Planned Breaking Changes
- GraphQL endpoint introduction
- Pagination change from cursor to page-based
- Bulk operations restructure

#### Planned Additions
- Advanced analytics endpoints
- Time tracking APIs
- Resource management
- Portfolio/program management
- Advanced reporting
- Integration marketplace

---

## Version Support

| Version | Status | Released | EOL | Support Level |
|---------|--------|----------|-----|---------------|
| 1.0.x   | Active | 2026-02-15 | TBD | Full support |
| 2.0.x   | Planned | TBD | TBD | N/A |

## Deprecation Policy

- Deprecated features will be marked with `Deprecation: true` header
- Sunset date will be included in `Sunset` header
- Minimum 6 months notice before removal
- Migration guide provided for breaking changes
- Alternative endpoint referenced in `Link` header

## Support

For questions or issues:
- Documentation: http://localhost:8000/api/docs/
- Issues: https://github.com/bugstracker/bugstracker/issues
- Email: api-support@bugstracker.com
