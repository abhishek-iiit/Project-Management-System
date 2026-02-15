"""
Test settings - inherits from base settings.
Optimized for fast test execution.
"""

from .base import *

# SECURITY WARNING: keep the secret key used in testing secret!
SECRET_KEY = 'test-secret-key-for-testing-only-do-not-use-in-production'

DEBUG = True

# Use PostgreSQL test database for consistency with production
# Can use SQLite for faster tests if needed
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'bugstracker_test',
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default='postgres'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'ATOMIC_REQUESTS': True,
        'CONN_MAX_AGE': 0,  # Close connections after each request in tests
        'TEST': {
            'NAME': 'bugstracker_test',
            'CHARSET': 'UTF8',
        }
    }
}

# Password hashers - use fast hasher for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable migrations for faster test db creation
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None

# MIGRATION_MODULES = DisableMigrations()

# Celery - always eager in tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Email - use in-memory backend
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Disable throttling in tests
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []

# Cache - use local memory cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Logging - minimal in tests
LOGGING['handlers']['console']['level'] = 'ERROR'
LOGGING['loggers']['django']['level'] = 'ERROR'

# Elasticsearch - use mock in tests
ELASTICSEARCH_DSL = {
    'default': {
        'hosts': 'localhost:9200'
    },
}
ELASTICSEARCH_DSL_AUTOSYNC = False

# Channels - in-memory layer for tests
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer'
    }
}

# Media files - use temp directory
MEDIA_ROOT = BASE_DIR / 'test_media'

# JWT settings - shorter lifetimes for tests
SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'] = timedelta(minutes=5)
SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'] = timedelta(minutes=10)

# CORS - allow all origins in tests
CORS_ALLOW_ALL_ORIGINS = True

# CSRF - disable secure cookies for tests
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# Maintenance mode - disabled in tests
MAINTENANCE_MODE = False

# Rate limiting - disabled in tests
RATE_LIMITING_ENABLED = False

# Test-specific settings
TESTING = True

# Disable middleware that might interfere with tests
MIDDLEWARE_TO_DISABLE = [
    'apps.audit.middleware.AuditMiddleware',  # Can be re-enabled per test
]

for middleware in MIDDLEWARE_TO_DISABLE:
    if middleware in MIDDLEWARE:
        MIDDLEWARE.remove(middleware)

# Coverage exclude patterns
COVERAGE_EXCLUDE_PATTERNS = [
    '*/migrations/*',
    '*/tests/*',
    '*/test_*.py',
    '*_test.py',
    'manage.py',
    'config/wsgi.py',
    'config/asgi.py',
]

print("🧪 Test settings loaded")
