"""
Security settings for BugsTracker.

This module contains all security-related settings that should be
included in the production settings file.
"""

# SECURITY WARNING: keep the secret key used in production secret!
# This should be loaded from environment variables
import os

SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable must be set")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Hosts/domain names that are valid for this site
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')
if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['']:
    raise ValueError("ALLOWED_HOSTS must be configured in production")

# ============================================================================
# HTTPS/SSL SETTINGS
# ============================================================================

# Force HTTPS redirect
SECURE_SSL_REDIRECT = True

# HTTP Strict Transport Security (HSTS)
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Secure proxy SSL header
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ============================================================================
# COOKIE SECURITY
# ============================================================================

# Cookies only sent over HTTPS
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Prevent JavaScript access to session cookie
SESSION_COOKIE_HTTPONLY = True

# SameSite attribute for cookies (prevent CSRF)
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

# Cookie age (2 weeks)
SESSION_COOKIE_AGE = 1209600

# Cookie names
SESSION_COOKIE_NAME = 'bugstracker_session'
CSRF_COOKIE_NAME = 'bugstracker_csrf'

# ============================================================================
# CONTENT SECURITY
# ============================================================================

# Prevent browsers from guessing content type
SECURE_CONTENT_TYPE_NOSNIFF = True

# Enable browser XSS protection
SECURE_BROWSER_XSS_FILTER = True

# Prevent clickjacking
X_FRAME_OPTIONS = 'DENY'

# ============================================================================
# PASSWORD SECURITY
# ============================================================================

# Password hashers (Argon2 is most secure)
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        'OPTIONS': {
            'user_attributes': ('username', 'email', 'first_name', 'last_name'),
            'max_similarity': 0.7,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Password reset timeout (1 hour)
PASSWORD_RESET_TIMEOUT = 3600

# ============================================================================
# CORS (Cross-Origin Resource Sharing)
# ============================================================================

# Allowed origins for CORS
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',')

# Allow credentials (cookies)
CORS_ALLOW_CREDENTIALS = True

# Allowed methods
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# Allowed headers
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# ============================================================================
# CSRF PROTECTION
# ============================================================================

# Trusted origins for CSRF
CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')

# Use the HTTP_X_CSRFTOKEN header
CSRF_HEADER_NAME = 'HTTP_X_CSRFTOKEN'

# Require CSRF token for unsafe methods
CSRF_USE_SESSIONS = False
CSRF_COOKIE_HTTPONLY = False  # Must be False for JavaScript to read it

# ============================================================================
# RATE LIMITING
# ============================================================================

# Enable rate limiting
RATE_LIMIT_ENABLED = True

# Rate limit in debug mode
RATE_LIMIT_IN_DEBUG = False

# ============================================================================
# ADMIN SECURITY
# ============================================================================

# IP whitelist for admin access (optional)
# ADMIN_IP_WHITELIST = ['1.2.3.4', '5.6.7.8']

# Admin URL (change from default /admin/)
ADMIN_URL = os.environ.get('ADMIN_URL', 'admin/')

# ============================================================================
# FILE UPLOAD SECURITY
# ============================================================================

# Maximum upload size (100 MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100 MB

# Maximum number of fields in POST
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000

# File upload permissions
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755

# ============================================================================
# DATABASE SECURITY
# ============================================================================

# Connection max age (connection pooling)
CONN_MAX_AGE = 600  # 10 minutes

# Atomic requests (all requests in transaction)
ATOMIC_REQUESTS = False  # Set per-app as needed

# ============================================================================
# LOGGING & MONITORING
# ============================================================================

# Sentry DSN for error tracking
SENTRY_DSN = os.environ.get('SENTRY_DSN')

if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        environment=os.environ.get('ENVIRONMENT', 'production'),
        traces_sample_rate=0.1,  # 10% of transactions
        send_default_pii=False,  # Don't send PII
        before_send=lambda event, hint: event if not DEBUG else None,
    )

# ============================================================================
# API SECURITY
# ============================================================================

# JWT settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# REST Framework security settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
    },
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'EXCEPTION_HANDLER': 'apps.common.exceptions.custom_exception_handler',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'MAX_PAGE_SIZE': 100,
}

# ============================================================================
# MIDDLEWARE
# ============================================================================

# Security middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Static files
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Custom security middleware
    'apps.common.middleware.security_headers.SecurityHeadersMiddleware',
    'apps.common.middleware.security_headers.SecureRequestMiddleware',
    'apps.common.middleware.rate_limiting.RateLimitMiddleware',
    'apps.common.middleware.tenant_middleware.TenantMiddleware',
    'apps.common.middleware.audit_middleware.AuditMiddleware',
]

# ============================================================================
# SECURITY CHECKLIST
# ============================================================================

"""
Security Checklist:

[x] SECRET_KEY is strong and secret
[x] DEBUG = False in production
[x] ALLOWED_HOSTS is properly configured
[x] HTTPS enforced (SECURE_SSL_REDIRECT)
[x] HSTS enabled with long max-age
[x] Secure cookies (SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE)
[x] HttpOnly cookies (SESSION_COOKIE_HTTPONLY)
[x] Content security headers (X-Content-Type-Options, X-Frame-Options)
[x] Strong password hashing (Argon2)
[x] Password validators configured
[x] CORS properly configured
[x] CSRF protection enabled
[x] Rate limiting enabled
[x] File upload restrictions
[x] SQL injection prevention (ORM)
[x] XSS prevention (template escaping)
[x] Secure file permissions
[x] Error tracking (Sentry)
[x] Security middleware enabled

Additional recommendations:
- Enable 2FA for admin users
- Regular security audits
- Dependency vulnerability scanning
- Penetration testing
- Security awareness training
- Incident response plan
"""
