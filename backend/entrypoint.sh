#!/bin/bash
set -e

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# Start the Django development server in background
echo "Starting Django Development Server..."
python manage.py runserver 0.0.0.0:8000 &

# Start the server
echo "Starting RADIUS server..."
exec python manage.py start
