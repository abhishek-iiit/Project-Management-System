"""
Development settings - inherits from base settings.
"""

from .base import *

DEBUG = True

# Development-specific apps
INSTALLED_APPS += [
    # 'django_extensions',  # Not critical for now
    'debug_toolbar',
    'silk',
]

# Debug toolbar middleware
MIDDLEWARE += [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'silk.middleware.SilkyMiddleware',
]

# Internal IPs for debug toolbar
INTERNAL_IPS = [
    '127.0.0.1',
    'localhost',
]

# Email backend (console for development)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable HTTPS requirements in development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Django Debug Toolbar Configuration
DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
}

# Silk Configuration (SQL profiling)
SILKY_PYTHON_PROFILER = True
SILKY_PYTHON_PROFILER_BINARY = True
SILKY_AUTHENTICATION = True
SILKY_AUTHORISATION = True
SILKY_MAX_REQUEST_BODY_SIZE = 1024  # 1KB
SILKY_MAX_RESPONSE_BODY_SIZE = 1024  # 1KB
SILKY_INTERCEPT_PERCENT = 100
SILKY_MAX_RECORDED_REQUESTS = 10000

# Logging - more verbose in development
LOGGING['loggers']['django.db.backends'] = {
    'handlers': ['console'],
    'level': 'DEBUG',
    'propagate': False,
}

# Celery - eager execution in development (synchronous)
CELERY_TASK_ALWAYS_EAGER = config('CELERY_EAGER', default=True, cast=bool)
CELERY_TASK_EAGER_PROPAGATES = True

# Disable rate limiting in development
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []

# CORS - allow all origins in development
CORS_ALLOW_ALL_ORIGINS = True

print("🔧 Development settings loaded")
