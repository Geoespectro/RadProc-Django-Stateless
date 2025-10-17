#!/bin/bash
set -e
echo "🚀 Iniciando RadProc Web (Interfaz Django Stateless)..."
python manage.py collectstatic --noinput
python manage.py migrate --noinput
echo "🌐 Levantando servidor Gunicorn..."
exec gunicorn web.wsgi:application --bind 0.0.0.0:8000 --workers 3


