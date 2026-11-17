#!/bin/sh
set -eu
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py import_ingredients
if [ "${SEED_DEMO:-False}" = "True" ]; then
  python manage.py seed_demo
fi
exec gunicorn foodgram.wsgi:application \
  --bind 0.0.0.0:8000 --workers "${GUNICORN_WORKERS:-2}" \
  --timeout 60 --access-logfile - --error-logfile -
