#!/bin/sh
set -e

# Apply database migrations before serving (dev-friendly; for production
# with multiple replicas, run migrations as a separate step instead)
python manage.py migrate --noinput

exec "$@"
