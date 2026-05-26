#!/usr/bin/env bash
# Render.com start script — runs on every container start
set -o errexit

# DB migrations & initial admin user must run at runtime,
# because Render may not expose all env vars during build.
python manage.py migrate
python manage.py ensure_superuser

exec gunicorn portal_escola.wsgi:application

