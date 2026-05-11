#!/bin/sh

set -e

# Run database migrations
echo "Running database migrations"
python manage.py migrate

# Start the server
exec "$@"
