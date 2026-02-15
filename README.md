# BugsTracker - Production-Grade Jira-Equivalent System

Enterprise-level project management and issue tracking system built with Django, Django REST Framework, and React Native.

## 🚀 Features

- **Multi-tenancy**: Organization-based data isolation
- **Dynamic Workflows**: Fully configurable workflow engine
- **Agile Boards**: Scrum and Kanban boards with sprints
- **Advanced Search**: JQL-like query language powered by Elasticsearch
- **Automation Engine**: Event-driven automation rules
- **Real-time Updates**: WebSocket-based notifications
- **Custom Fields**: Flexible field definitions per project/issue type
- **Webhooks**: Outgoing webhook integrations
- **Audit Logging**: Complete activity and change tracking
- **API-First**: RESTful API with OpenAPI documentation

## 📋 Tech Stack

### Backend
- **Django 5.2.5** - Web framework
- **Django REST Framework 3.16.1** - API framework
- **PostgreSQL 16** - Primary database
- **Redis 7** - Caching, Celery broker, Channels layer
- **Elasticsearch 8** - Full-text search
- **Celery 5.4** - Async task processing
- **Django Channels 4** - WebSocket support

### Frontend (Coming Soon)
- **React Native** - Cross-platform mobile app
- **TypeScript** - Type safety
- **Zustand** - State management
- **React Query** - Server state management

## 🏗️ Architecture

```
┌─────────────────┐
│  React Native   │
│   Mobile App    │
└────────┬────────┘
         │ REST API + WebSocket
         ▼
┌─────────────────────────────────┐
│     Django REST Framework       │
│  ┌──────────┬──────────┐       │
│  │   Auth   │   Core   │       │
│  ├──────────┼──────────┤       │
│  │ Workflow │ Automation│       │
│  └──────────┴──────────┘       │
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│   PostgreSQL │ Redis │ ES       │
└─────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 16+
- Redis 7+
- Elasticsearch 8+
- Docker & Docker Compose (recommended)

### Option 1: Docker (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd BugsTracker
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start services with Docker Compose**
   ```bash
   cd infrastructure/docker
   docker-compose up -d
   ```

4. **Initialize database**
   ```bash
   docker-compose exec backend python manage.py migrate
   docker-compose exec backend python manage.py createsuperuser
   ```

5. **Access the application**
   - API: http://localhost:8000/api/v1/
   - Admin: http://localhost:8000/admin/
   - API Docs: http://localhost:8000/api/docs/
   - Flower (Celery): http://localhost:5555/

### Option 2: Local Development

1. **Clone and setup**
   ```bash
   git clone <repository-url>
   cd BugsTracker/backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements/development.txt
   ```

4. **Configure environment**
   ```bash
   cp ../.env.example ../.env
   # Edit .env with your database credentials
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Start development server**
   ```bash
   python manage.py runserver
   ```

8. **Start Celery worker (separate terminal)**
   ```bash
   celery -A config worker -l info
   ```

9. **Start Celery beat (separate terminal)**
   ```bash
   celery -A config beat -l info
   ```

## 📁 Project Structure

```
BugsTracker/
├── backend/
│   ├── apps/                      # Django applications
│   │   ├── common/               # Shared utilities
│   │   ├── accounts/             # User management
│   │   ├── organizations/        # Multi-tenancy
│   │   ├── projects/             # Project management
│   │   ├── issues/               # Issue tracking
│   │   ├── workflows/            # Workflow engine
│   │   ├── fields/               # Custom fields
│   │   ├── boards/               # Agile boards
│   │   ├── automation/           # Automation engine
│   │   ├── search/               # Search & JQL
│   │   ├── notifications/        # Notifications
│   │   ├── webhooks/             # Webhooks
│   │   ├── audit/                # Audit logging
│   │   └── analytics/            # Reporting
│   ├── config/                   # Django settings
│   ├── api/                      # API versioning
│   ├── tasks/                    # Celery tasks
│   └── requirements/             # Python dependencies
├── infrastructure/
│   ├── docker/                   # Docker configs
│   ├── kubernetes/               # K8s manifests
│   └── nginx/                    # Nginx configs
├── scripts/                      # Utility scripts
└── docs/                         # Documentation
```

## 🧪 Testing

Run tests with pytest:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=apps --cov-report=html

# Run specific app tests
pytest apps/issues/tests/

# Run parallel tests
pytest -n auto
```

## 📚 API Documentation

Once the server is running, visit:

- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

## 🔒 Security

- Multi-tenancy with organization-based isolation
- Row-level security via django-guardian
- JWT authentication with access/refresh tokens
- Rate limiting on all endpoints
- CORS protection
- SQL injection prevention
- XSS protection
- CSRF protection

## 🎯 Roadmap

### Phase 1: Foundation ✅ (Current)
- [x] Django project setup
- [x] Base models and middleware
- [x] Docker configuration
- [x] Celery integration

### Phase 2: Authentication (In Progress)
- [ ] User model and authentication
- [ ] Organization management
- [ ] JWT token handling
- [ ] Permission system

### Phase 3-17: Feature Development
See [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) for detailed roadmap.

## 👥 Contributing

This is a learning/portfolio project. Contributions, issues, and feature requests are welcome!

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- Django and DRF communities
- Atlassian Jira (inspiration)
- All open-source contributors

---

**Built with ❤️ using Django and following best practices from CLAUDE.md**
