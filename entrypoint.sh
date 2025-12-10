#!/bin/bash
set -e

# Generate SSL certificates if they don't exist
echo "Checking SSL certificates..."
/usr/local/bin/generate-ssl.sh

# Wait for MySQL to be ready (additional safety check)
echo "Waiting for MySQL to be ready..."
max_attempts=30
attempt=0
while ! mysqladmin -h"${MYSQL_HOST}" -P"${MYSQL_PORT:-3306}" --protocol=tcp --skip-ssl \
       -u"${MYSQL_USER}" -p"${MYSQL_PASSWORD}" ping >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ $attempt -ge $max_attempts ]; then
        echo "Error: MySQL not available after $max_attempts attempts"
        # Show the actual error for debugging
        mysqladmin -h"${MYSQL_HOST}" -P"${MYSQL_PORT:-3306}" --protocol=tcp --skip-ssl \
                   -u"${MYSQL_USER}" -p"${MYSQL_PASSWORD}" ping
        exit 1
    fi
    echo "Waiting for MySQL... (attempt $attempt/$max_attempts)"
    sleep 2
done
echo "MySQL is ready!"

# Start Nginx
echo "Starting Nginx..."
nginx

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# Start the Django development server in background
echo "Starting Django Development Server..."
python manage.py runserver 0.0.0.0:8000 &

# Start the RADIUS server
echo "Starting RADIUS server..."
exec python manage.py start
