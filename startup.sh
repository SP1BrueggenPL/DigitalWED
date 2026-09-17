#!/bin/bash
# Startup command dla Azure App Service (Linux, Python) - ustaw w:
# Configuration -> Stack settings -> Startup Command: bash startup.sh
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput
gunicorn wed_platform.wsgi:application --bind=0.0.0.0:8000 --workers 2 --timeout 120
