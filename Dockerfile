# syntax=docker/dockerfile:1
# Sırlar image içine yazılmaz; Railway çalışma zamanında Variables ile verir.
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

COPY . .

# collectstatic: yalnızca build katmanı için sahte anahtar (gerçek SECRET_KEY yok).
RUN SECRET_KEY=build-collectstatic-only \
    DEBUG=True \
    DATABASE_URL= \
    ALLOWED_HOSTS=* \
    python manage.py collectstatic --noinput

ENV PORT=8000
EXPOSE 8000

COPY scripts/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
