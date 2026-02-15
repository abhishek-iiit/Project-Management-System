# API Testing Guide

This guide covers testing the BugsTracker API using various tools and methods.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Using Swagger UI](#using-swagger-ui)
- [Using Postman](#using-postman)
- [Using cURL](#using-curl)
- [Using Python](#using-python)
- [Automated Testing](#automated-testing)
- [Load Testing](#load-testing)
- [WebSocket Testing](#websocket-testing)

## Prerequisites

### Development Server

Start the development server:

```bash
cd backend
python manage.py runserver
```

The API will be available at `http://localhost:8000/api/v1/`

### Test Database

Create test data:

```bash
python manage.py migrate
python manage.py seed_data  # If available
```

## Using Swagger UI

Swagger UI provides an interactive API explorer.

### Access Swagger UI

Navigate to: `http://localhost:8000/api/docs/`

### Authentication in Swagger UI

1. Click the **Authorize** button (top right)
2. Enter your JWT token in the format: `Bearer <token>`
3. Click **Authorize**
4. Close the dialog

All subsequent requests will include the authorization header.

### Making Requests

1. Expand an endpoint group (e.g., "Issues")
2. Click on a specific endpoint
3. Click **Try it out**
4. Fill in required parameters
5. Click **Execute**
6. View the response below

### Tips

- Use the **Schemas** section to see model definitions
- Responses include example values
- Status codes and descriptions are provided
- Download the OpenAPI schema using the link at the top

## Using Postman

### Import Collection

1. Open Postman
2. Click **Import**
3. Select `docs/api/postman_collection.json`
4. Click **Import**

### Configure Environment

1. Click the environment dropdown (top right)
2. Click **Create Environment**
3. Add variables:
   - `base_url`: `http://localhost:8000/api/v1`
   - `access_token`: (leave empty)
   - `refresh_token`: (leave empty)
4. Click **Save**
5. Select the environment

### Workflow

1. **Register or Login**
   - Navigate to **Authentication > Login**
   - Update credentials in the body
   - Send request
   - Token is automatically saved to environment

2. **Create Organization**
   - Navigate to **Organizations > Create Organization**
   - Send request
   - Organization ID is automatically saved

3. **Create Project**
   - Navigate to **Projects > Create Project**
   - Send request
   - Project ID is automatically saved

4. **Create Issue**
   - Navigate to **Issues > Create Issue**
   - Send request
   - Issue ID is automatically saved

5. **Explore Other Endpoints**
   - All subsequent requests use the saved tokens

### Auto-saving Variables

The collection includes test scripts that automatically save:
- `access_token` from login
- `organization_id` from organization creation
- `project_id` from project creation
- `issue_id` from issue creation

## Using cURL

### Basic Authentication Flow

```bash
# Set base URL
BASE_URL="http://localhost:8000/api/v1"

# 1. Login
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123!"
  }')

# Extract access token
TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.data.access')

# 2. List issues with authentication
curl -X GET "$BASE_URL/issues/" \
  -H "Authorization: Bearer $TOKEN"

# 3. Create issue
curl -X POST "$BASE_URL/issues/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project": "550e8400-e29b-41d4-a716-446655440000",
    "summary": "Test issue",
    "issue_type": "task",
    "priority": "medium"
  }'

# 4. Search with JQL
curl -X GET "$BASE_URL/search/?jql=status%3Din_progress" \
  -H "Authorization: Bearer $TOKEN"
```

### Handling Pagination

```bash
# Get page 2
curl -X GET "$BASE_URL/issues/?page=2&page_size=25" \
  -H "Authorization: Bearer $TOKEN"

# Follow next URL
NEXT_URL=$(curl -s -X GET "$BASE_URL/issues/" \
  -H "Authorization: Bearer $TOKEN" \
  | jq -r '.next')

curl -X GET "$NEXT_URL" \
  -H "Authorization: Bearer $TOKEN"
```

### Rate Limit Headers

```bash
# Check rate limit headers
curl -i -X GET "$BASE_URL/issues/" \
  -H "Authorization: Bearer $TOKEN" \
  | grep "X-RateLimit"
```

## Using Python

### requests Library

```python
import requests
from pprint import pprint

BASE_URL = "http://localhost:8000/api/v1"

class BugsTrackerClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.token = None
        self.session = requests.Session()

    def login(self, email, password):
        """Authenticate and store token."""
        response = self.session.post(
            f"{self.base_url}/auth/login/",
            json={"email": email, "password": password}
        )
        response.raise_for_status()
        data = response.json()['data']
        self.token = data['access']
        self.session.headers.update({
            'Authorization': f'Bearer {self.token}'
        })
        return data

    def list_issues(self, **params):
        """List issues with optional filters."""
        response = self.session.get(
            f"{self.base_url}/issues/",
            params=params
        )
        response.raise_for_status()
        return response.json()

    def create_issue(self, **data):
        """Create a new issue."""
        response = self.session.post(
            f"{self.base_url}/issues/",
            json=data
        )
        response.raise_for_status()
        return response.json()['data']

    def search(self, jql, **params):
        """Search with JQL."""
        params['jql'] = jql
        response = self.session.get(
            f"{self.base_url}/search/",
            params=params
        )
        response.raise_for_status()
        return response.json()

# Usage
client = BugsTrackerClient(BASE_URL)

# Login
user = client.login("user@example.com", "SecurePassword123!")
print(f"Logged in as: {user['email']}")

# List issues
issues = client.list_issues(page_size=10, ordering='-created_at')
pprint(issues['results'])

# Create issue
new_issue = client.create_issue(
    project="550e8400-e29b-41d4-a716-446655440000",
    summary="Test from Python",
    issue_type="bug",
    priority="high"
)
print(f"Created issue: {new_issue['key']}")

# Search
results = client.search('project="PROJ" AND priority=high')
pprint(results)
```

### pytest Integration

```python
# tests/test_api.py
import pytest
import requests

@pytest.fixture
def api_client():
    """API client fixture."""
    return BugsTrackerClient("http://localhost:8000/api/v1")

@pytest.fixture
def authenticated_client(api_client):
    """Authenticated client fixture."""
    api_client.login("test@example.com", "password")
    return api_client

def test_list_issues(authenticated_client):
    """Test listing issues."""
    response = authenticated_client.list_issues()
    assert 'results' in response
    assert isinstance(response['results'], list)

def test_create_issue(authenticated_client):
    """Test creating issue."""
    issue = authenticated_client.create_issue(
        project="550e8400-e29b-41d4-a716-446655440000",
        summary="Test issue",
        issue_type="task"
    )
    assert 'id' in issue
    assert issue['summary'] == "Test issue"

def test_rate_limit():
    """Test rate limiting."""
    client = BugsTrackerClient("http://localhost:8000/api/v1")

    # Make requests until rate limited
    for i in range(150):
        response = requests.get(f"{client.base_url}/issues/")
        if response.status_code == 429:
            assert 'Retry-After' in response.headers
            break
```

## Automated Testing

### Unit Tests

Run API unit tests:

```bash
pytest apps/*/tests/test_api.py -v
```

### Integration Tests

Run integration tests:

```bash
pytest tests/integration/ -v
```

### Coverage

Generate coverage report:

```bash
pytest --cov=apps --cov-report=html
open htmlcov/index.html
```

## Load Testing

### Using Locust

Create `locustfile.py`:

```python
from locust import HttpUser, task, between

class BugsTrackerUser(HttpUser):
    wait_time = between(1, 3)
    token = None

    def on_start(self):
        """Login before starting."""
        response = self.client.post("/api/v1/auth/login/", json={
            "email": "user@example.com",
            "password": "password"
        })
        self.token = response.json()['data']['access']
        self.client.headers.update({
            'Authorization': f'Bearer {self.token}'
        })

    @task(3)
    def list_issues(self):
        """List issues (most common operation)."""
        self.client.get("/api/v1/issues/")

    @task(1)
    def create_issue(self):
        """Create issue (less common)."""
        self.client.post("/api/v1/issues/", json={
            "project": "550e8400-e29b-41d4-a716-446655440000",
            "summary": "Load test issue",
            "issue_type": "task"
        })

    @task(2)
    def search(self):
        """Search issues."""
        self.client.get("/api/v1/search/?jql=status=in_progress")
```

Run load test:

```bash
locust -f locustfile.py --host=http://localhost:8000
```

Open web UI at `http://localhost:8089`

### Performance Targets

- **Response time p95**: < 500ms
- **Response time p99**: < 1s
- **Throughput**: 10,000 req/min
- **Error rate**: < 1%

## WebSocket Testing

### Using Browser Console

```javascript
// Connect to notifications
const ws = new WebSocket('ws://localhost:8000/ws/notifications/?token=YOUR_TOKEN');

ws.onopen = () => {
  console.log('Connected');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Notification:', data);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Disconnected');
};
```

### Using Python

```python
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/ws/notifications/?token=YOUR_TOKEN"

    async with websockets.connect(uri) as websocket:
        print("Connected")

        # Receive messages
        async for message in websocket:
            data = json.loads(message)
            print(f"Received: {data}")

# Run
asyncio.run(test_websocket())
```

## Debugging

### Enable Debug Mode

In `.env`:

```
DEBUG=True
```

### Django Debug Toolbar

Access debug toolbar: `http://localhost:8000/__debug__/`

### SQL Query Logging

In settings:

```python
LOGGING = {
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
        },
    },
}
```

### API Profiling

Use django-silk: `http://localhost:8000/silk/`

## Common Issues

### 401 Unauthorized

- **Cause**: Missing or expired token
- **Fix**: Login again to get fresh token

### 429 Too Many Requests

- **Cause**: Rate limit exceeded
- **Fix**: Wait for `Retry-After` seconds

### 500 Internal Server Error

- **Cause**: Server error
- **Fix**: Check server logs for stack trace

### CORS Error

- **Cause**: Origin not in allowed origins
- **Fix**: Add origin to `CORS_ALLOWED_ORIGINS` in settings

## Best Practices

1. **Always check status codes** before processing response
2. **Handle rate limits** gracefully with retries
3. **Use pagination** for large result sets
4. **Cache responses** when appropriate
5. **Close WebSocket connections** when done
6. **Use field filtering** to reduce payload size
7. **Monitor rate limit headers** to avoid throttling
8. **Implement exponential backoff** for retries

## Resources

- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **OpenAPI Schema**: http://localhost:8000/api/schema/
- **Postman Collection**: `docs/api/postman_collection.json`
