#!/bin/sh
set -e
PORT="${PORT:-8000}"
export PORT

# Tek serviste: Gunicorn ile aynı konteynerde Celery (ayrı Railway servisi gerekmez).
# Broker: CELERY_BROKER_URL veya REDIS_URL. Kapatmak için RUN_CELERY_IN_WEB boş bırakın.
if [ "${RUN_CELERY_IN_WEB:-}" = "1" ] && [ -n "${CELERY_BROKER_URL:-${REDIS_URL:-}}" ]; then
  echo "[docker-entrypoint] RUN_CELERY_IN_WEB=1: Celery worker + beat (background, same container)"
  celery -A core worker -l info &
  celery -A core beat -l info &
elif [ "${RUN_CELERY_IN_WEB:-}" = "1" ]; then
  echo "[docker-entrypoint] WARN: RUN_CELERY_IN_WEB=1 but CELERY_BROKER_URL and REDIS_URL are empty; skipping Celery"
fi

echo "[docker-entrypoint] gunicorn 0.0.0.0:${PORT}"
exec gunicorn core.wsgi:application \
  --bind "0.0.0.0:${PORT}" \
  --workers "${WEB_CONCURRENCY:-1}" \
  --threads 2 \
  --timeout 120 \
  --graceful-timeout 60 \
  --access-logfile - \
  --error-logfile -
