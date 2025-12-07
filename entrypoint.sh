#!/bin/bash
set -e

# Generate SSL certificates if they don't exist
echo "Checking SSL certificates..."
/usr/local/bin/generate-ssl.sh

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
