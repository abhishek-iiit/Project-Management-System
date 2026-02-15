#!/bin/bash

# Database initialization script for BugsTracker

set -e

echo "🗄️  Initializing BugsTracker database..."

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
until python manage.py shell -c "from django.db import connection; connection.cursor()" 2>/dev/null; do
    echo "PostgreSQL is unavailable - sleeping"
    sleep 1
done

echo "✅ PostgreSQL is up"

# Run migrations
echo "Running migrations..."
python manage.py makemigrations
python manage.py migrate

# Create superuser if it doesn't exist
echo "Creating superuser..."
python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='admin@bugstracker.com').exists():
    User.objects.create_superuser(
        email='admin@bugstracker.com',
        username='admin',
        password='admin123',
        first_name='Admin',
        last_name='User'
    )
    print('✅ Superuser created: admin@bugstracker.com / admin123')
else:
    print('ℹ️  Superuser already exists')
EOF

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "✅ Database initialization complete!"
