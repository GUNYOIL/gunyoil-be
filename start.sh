#!/bin/sh
set -e

python manage.py migrate
python manage.py seed_exercises --prune
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000
