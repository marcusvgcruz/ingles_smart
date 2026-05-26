#!/usr/bin/env bash
# Render.com start script — runs on every container start
set -o errexit

echo "==> [start.sh] migrate"
python manage.py migrate --noinput

echo "==> [start.sh] ensure_superuser"
python manage.py ensure_superuser

echo "==> [start.sh] starting gunicorn"
exec gunicorn portal_escola.wsgi:application
