#!/bin/sh

set -e

# Run database migrations
echo "---Running database migrations---"
python manage.py migrate

# Load fake posts for demonstration
echo "---Load initial data---"
python manage.py loaddata example_data.json

# Serve static files
echo "---Collects the static files---"
python manage.py collectstatic --noinput

# Start the server
exec "$@"
