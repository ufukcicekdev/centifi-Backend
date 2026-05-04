# Docker dışı (ör. yerel): gömülü Celery için RUN_CELERY_IN_WEB=1 ve broker URL gerekir.
web: sh -c 'if [ "${RUN_CELERY_IN_WEB:-}" = "1" ] && [ -n "${CELERY_BROKER_URL:-${REDIS_URL:-}}" ]; then celery -A core worker -l info & celery -A core beat -l info & fi; exec gunicorn core.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --threads 2 --timeout 120 --graceful-timeout 60'
