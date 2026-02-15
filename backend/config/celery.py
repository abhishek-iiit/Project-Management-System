"""
Celery configuration for BugsTracker.
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

# Create Celery app
app = Celery('bugstracker')

# Load config from Django settings with CELERY namespace
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

# Celery Beat Schedule (Periodic Tasks)
app.conf.beat_schedule = {
    # Example: Clean up old audit logs every day at 2 AM
    'cleanup-old-audit-logs': {
        'task': 'apps.audit.tasks.cleanup_old_logs',
        'schedule': crontab(hour=2, minute=0),
    },
    # Example: Update search index every 30 minutes
    'update-search-index': {
        'task': 'apps.search.tasks.update_index',
        'schedule': crontab(minute='*/30'),
    },
    # Example: Send notification digest emails every hour
    'send-notification-digest': {
        'task': 'apps.notifications.tasks.send_digest_emails',
        'schedule': crontab(minute=0),
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery setup."""
    print(f'Request: {self.request!r}')
