#!/bin/sh

set -e

# Run database migrations
echo "Running database migrations"
python manage.py migrate

# Load fake posts for demonstration
echo "Load initial data"
python manage.py loaddata example_data.json

# Start the server
exec "$@"
