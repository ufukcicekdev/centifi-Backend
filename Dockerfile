# syntax=docker/dockerfile:1
# Build context bazen monorepo kökü olabiliyor; harici scripts/ COPY güvenilir değil.
# Entrypoint imaj içinde yazılır (sırlar yine runtime Variables).
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=core.settings

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python3 <<'PY'
script = r'''#!/bin/sh
set -e
PORT="${PORT:-8000}"
export PORT
echo "[docker-entrypoint] listening on 0.0.0.0:${PORT}"
exec gunicorn core.wsgi:application \
  --bind "0.0.0.0:${PORT}" \
  --workers "${WEB_CONCURRENCY:-1}" \
  --threads 2 \
  --timeout 120 \
  --graceful-timeout 60 \
  --access-logfile - \
  --error-logfile -
'''
open("/docker-entrypoint.sh", "w").write(script)
import os
os.chmod("/docker-entrypoint.sh", 0o755)
PY

COPY . .

# collectstatic: yalnızca build katmanı için sahte anahtar (gerçek SECRET_KEY yok).
RUN SECRET_KEY=build-collectstatic-only \
    DEBUG=True \
    DATABASE_URL= \
    ALLOWED_HOSTS=* \
    python manage.py collectstatic --noinput

ENV PORT=8000
EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
