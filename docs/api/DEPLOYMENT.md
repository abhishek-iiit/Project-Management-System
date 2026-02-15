# API Documentation Deployment Guide

This guide covers deploying and configuring the BugsTracker API documentation.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Generating OpenAPI Schema](#generating-openapi-schema)
- [Hosting Documentation](#hosting-documentation)
- [Custom Domain](#custom-domain)
- [Authentication](#authentication)
- [Versioning](#versioning)
- [Monitoring](#monitoring)
- [Best Practices](#best-practices)

## Prerequisites

### Required Packages

Ensure these packages are installed:

```txt
drf-spectacular==0.28.0
PyYAML==6.0.2
```

### Environment Variables

Configure in `.env`:

```bash
# API Documentation
API_DOCS_ENABLED=True
API_DOCS_AUTH_REQUIRED=False
SWAGGER_UI_ENABLED=True
REDOC_UI_ENABLED=True

# API Settings
API_VERSION=1.0.0
API_TITLE="BugsTracker API"
API_DESCRIPTION="Production-grade issue tracking system"
```

## Generating OpenAPI Schema

### Using Management Command

Generate schema files:

```bash
# Generate both YAML and JSON
python manage.py generate_openapi_schema

# Generate only YAML
python manage.py generate_openapi_schema --format yaml

# Generate only JSON
python manage.py generate_openapi_schema --format json

# Custom output directory
python manage.py generate_openapi_schema --output /path/to/output

# With validation
python manage.py generate_openapi_schema --validate
```

### Output Files

Generated files are saved to `docs/api/`:
- `openapi.yaml` - YAML format schema
- `openapi.json` - JSON format schema

### Automated Generation

Add to CI/CD pipeline:

```yaml
# .github/workflows/ci.yml
- name: Generate API Schema
  run: |
    python manage.py generate_openapi_schema --validate
    git add docs/api/openapi.*
    git commit -m "Update API schema" || true
```

## Hosting Documentation

### Option 1: Serve with Django (Development)

Documentation is automatically available at:

- **Swagger UI**: `http://localhost:8000/api/docs/`
- **ReDoc**: `http://localhost:8000/api/redoc/`
- **Schema**: `http://localhost:8000/api/schema/`

Configure in `urls.py`:

```python
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path('api/schema/', SpectacularAPIView.as_view(), name='api-schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='api-schema'), name='api-docs'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='api-schema'), name='api-redoc'),
]
```

### Option 2: Serve with Nginx (Production)

Serve static schema with Nginx:

```nginx
# nginx.conf
server {
    listen 80;
    server_name docs.bugstracker.com;

    location / {
        root /var/www/api-docs;
        index index.html;
    }

    location /openapi.yaml {
        alias /var/www/api-docs/openapi.yaml;
        add_header Content-Type application/x-yaml;
    }

    location /openapi.json {
        alias /var/www/api-docs/openapi.json;
        add_header Content-Type application/json;
    }
}
```

### Option 3: GitHub Pages

Host on GitHub Pages:

1. Generate schema files
2. Create `docs/index.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <title>BugsTracker API Documentation</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
        window.onload = () => {
            window.ui = SwaggerUIBundle({
                url: './openapi.yaml',
                dom_id: '#swagger-ui',
            });
        };
    </script>
</body>
</html>
```

3. Push to GitHub
4. Enable GitHub Pages in repository settings

### Option 4: Dedicated Hosting (Stoplight, ReadMe.io)

Upload `openapi.yaml` to:

- **Stoplight**: https://stoplight.io
- **ReadMe**: https://readme.com
- **SwaggerHub**: https://swaggerhub.com
- **Postman**: https://www.postman.com

## Custom Domain

### Configure DNS

Add CNAME record:

```
docs.bugstracker.com -> your-server.com
```

### Configure SSL

Use Let's Encrypt:

```bash
sudo certbot --nginx -d docs.bugstracker.com
```

### Update CORS Settings

Add docs domain to allowed origins:

```python
# settings.py
CORS_ALLOWED_ORIGINS = [
    'https://docs.bugstracker.com',
    'https://app.bugstracker.com',
]
```

## Authentication

### Protect Documentation

Require authentication for docs access:

```python
# urls.py
from django.contrib.auth.decorators import login_required

urlpatterns = [
    path('api/docs/',
         login_required(SpectacularSwaggerView.as_view(url_name='api-schema')),
         name='api-docs'),
]
```

### API Key for Schema Access

Protect schema endpoint:

```python
# middleware.py
class APIDocsAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/api/schema/'):
            api_key = request.headers.get('X-API-Key')
            if api_key != settings.DOCS_API_KEY:
                return JsonResponse({'error': 'Invalid API key'}, status=401)
        return self.get_response(request)
```

### Basic Auth with Nginx

```nginx
location /api/docs/ {
    auth_basic "API Documentation";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://backend;
}
```

## Versioning

### Multi-Version Documentation

Serve multiple API versions:

```python
# urls.py
urlpatterns = [
    # V1 Documentation
    path('api/v1/schema/',
         SpectacularAPIView.as_view(api_version='v1'),
         name='api-schema-v1'),
    path('api/v1/docs/',
         SpectacularSwaggerView.as_view(url_name='api-schema-v1'),
         name='api-docs-v1'),

    # V2 Documentation
    path('api/v2/schema/',
         SpectacularAPIView.as_view(api_version='v2'),
         name='api-schema-v2'),
    path('api/v2/docs/',
         SpectacularSwaggerView.as_view(url_name='api-schema-v2'),
         name='api-docs-v2'),
]
```

### Version Dropdown

Add version selector to Swagger UI:

```python
SPECTACULAR_SETTINGS = {
    'SWAGGER_UI_SETTINGS': {
        'urls': [
            {'name': 'v1', 'url': '/api/v1/schema/'},
            {'name': 'v2', 'url': '/api/v2/schema/'},
        ],
        'urls.primaryName': 'v1',
    },
}
```

## Monitoring

### Track Documentation Usage

Log documentation access:

```python
# middleware.py
class DocsAnalyticsMiddleware:
    def __call__(self, request):
        if request.path.startswith('/api/docs/'):
            # Log to analytics
            logger.info(f'Docs accessed by {request.user}')
        return self.get_response(request)
```

### Monitor Schema Health

Check schema validity in health endpoint:

```python
@api_view(['GET'])
def health_check(request):
    # Check schema generation
    try:
        from drf_spectacular.generators import SchemaGenerator
        generator = SchemaGenerator()
        schema = generator.get_schema()
        schema_status = 'ok'
    except Exception as e:
        schema_status = 'error'

    return Response({
        'status': 'healthy',
        'checks': {
            'schema': schema_status,
        }
    })
```

## Best Practices

### 1. Keep Schema Updated

Regenerate schema on every deployment:

```bash
# deploy.sh
python manage.py generate_openapi_schema --validate
python manage.py collectstatic --noinput
```

### 2. Add Examples

Include request/response examples:

```python
from drf_spectacular.utils import extend_schema, OpenApiExample

@extend_schema(
    examples=[
        OpenApiExample(
            'Create Issue',
            value={'summary': 'Bug report', 'priority': 'high'},
            request_only=True,
        ),
    ]
)
def create(self, request):
    pass
```

### 3. Describe Parameters

Add descriptions to query parameters:

```python
@extend_schema(
    parameters=[
        OpenApiParameter(
            name='status',
            description='Filter by issue status',
            required=False,
            type=str,
        ),
    ]
)
def list(self, request):
    pass
```

### 4. Tag Endpoints

Group endpoints logically:

```python
@extend_schema(tags=['Issues'])
class IssueViewSet(viewsets.ModelViewSet):
    pass
```

### 5. Document Errors

Include error response examples:

```python
@extend_schema(
    responses={
        200: IssueSerializer,
        400: OpenApiResponse(description='Invalid input'),
        404: OpenApiResponse(description='Issue not found'),
    }
)
def retrieve(self, request, pk=None):
    pass
```

### 6. Version Documentation

Keep changelog updated:

```markdown
# docs/api/CHANGELOG.md
## [1.1.0] - 2026-03-01
### Added
- New bulk operations endpoint
- Enhanced search capabilities
```

### 7. Test Documentation

Validate schema in tests:

```python
def test_schema_generation():
    from django.test import Client
    client = Client()
    response = client.get('/api/schema/')
    assert response.status_code == 200
    schema = response.json()
    assert 'openapi' in schema
```

### 8. Cache Schema

Cache generated schema:

```python
SPECTACULAR_SETTINGS = {
    'SERVE_INCLUDE_SCHEMA': False,  # Don't include in responses
    'COMPONENT_SPLIT_REQUEST': True,  # Reuse components
}
```

### 9. Secure Production Docs

Restrict access in production:

```python
# settings/production.py
if not DEBUG:
    # Require authentication
    SPECTACULAR_SETTINGS['SERVE_AUTHENTICATION'] = [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ]
```

### 10. Provide Postman Collection

Export and maintain Postman collection:

```bash
# Generate from schema
curl http://localhost:8000/api/schema/ \
  | openapi2postmanv2 -s - -o postman_collection.json
```

## Troubleshooting

### Schema Generation Fails

Check for circular imports:

```bash
python manage.py check
python manage.py spectacular --validate --fail-on-warn
```

### Missing Endpoints

Ensure views are registered:

```python
# urls.py
from rest_framework.routers import DefaultRouter
from apps.issues.views import IssueViewSet

router = DefaultRouter()
router.register(r'issues', IssueViewSet)
```

### Incorrect Schemas

Specify serializer explicitly:

```python
@extend_schema(responses=IssueSerializer)
def custom_action(self, request):
    pass
```

### CORS Issues

Update CORS settings:

```python
CORS_ALLOW_HEADERS = [
    'authorization',
    'content-type',
]
```

## Resources

- **drf-spectacular docs**: https://drf-spectacular.readthedocs.io/
- **OpenAPI spec**: https://spec.openapis.org/oas/v3.1.0
- **Swagger UI**: https://swagger.io/tools/swagger-ui/
- **ReDoc**: https://redocly.com/redoc/

## Support

For deployment issues:
- Documentation: https://docs.bugstracker.com
- Email: devops@bugstracker.com
- Slack: #api-docs
