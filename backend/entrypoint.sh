#!/bin/bash
set -e

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# Start the server
echo "Starting RADIUS server..."
exec python manage.py start
