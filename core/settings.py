from pathlib import Path
from dotenv import load_dotenv
import os

import dj_database_url

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-change-me")
DEBUG = os.getenv("DEBUG", "True") == "True"
ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv("ALLOWED_HOSTS", "*").split(",")
    if h.strip()
]
# Container içi / bazı probe'lar 127.0.0.1 Host kullanır; * değilse ekle.
if "*" not in ALLOWED_HOSTS:
    for _h in ("127.0.0.1", "localhost", "[::1]"):
        if _h not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(_h)

INSTALLED_APPS = [
    "storages",
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    # Local
    "users",
    "expenses",
    "ai",
    "django_celery_beat",
]

MIDDLEWARE = [
    "core.middleware.HealthCheckMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "email_templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"

# ── Database ──────────────────────────────────────────────────────────────────
# Railway / Heroku Postgres: set DATABASE_URL (takes precedence over discrete vars below).
DATABASES = {
    "default": {
        "ENGINE": os.getenv("DATABASE_ENGINE", "django.db.backends.postgresql"),
        "NAME": os.getenv("DATABASE_NAME", "expensetracker"),
        "USER": os.getenv("DATABASE_USER", "postgres"),
        "PASSWORD": os.getenv("DATABASE_PASSWORD", ""),
        "HOST": os.getenv("DATABASE_HOST", "localhost"),
        "PORT": os.getenv("DATABASE_PORT", "5432"),
        "OPTIONS": {
            "sslmode": os.getenv("DATABASE_SSLMODE", "require"),
        },
    }
}

if os.getenv("DATABASE_URL"):
    DATABASES["default"] = dj_database_url.config(
        conn_max_age=600,
        conn_health_checks=True,
        ssl_require=True,
    )

# ── Auth ──────────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ── DRF ───────────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

from datetime import timedelta
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=7),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
}

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:8081,http://127.0.0.1:8081",
    ).split(",")
    if o.strip()
]

# ── i18n ──────────────────────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Manifest sürümü build/runtime uyuşmazsa worker açılışında sorun çıkarabiliyor; prod’da sıkıştırılmış statik yeterli.
_WHITENOISE_STATICFILES = {
    "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
}

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    USE_X_FORWARDED_HOST = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# ── RevenueCat (Play / App Store abonelik) ────────────────────────────────────
REVENUECAT_ENTITLEMENT_ID = (os.getenv("REVENUECAT_ENTITLEMENT_ID") or "pro").strip()
REVENUECAT_WEBHOOK_SECRET = (os.getenv("REVENUECAT_WEBHOOK_SECRET") or "").strip()
REVENUECAT_SECRET_API_KEY = (os.getenv("REVENUECAT_SECRET_API_KEY") or "").strip()

# ── Email — rapor: HTML tablo + CSV ek ────────────────────────────────────────
# Öncelik: SMTP2GO REST API (`SMTP2GO_API_KEY` + `SMTP2GO_FROM_EMAIL`). Yoksa SMTP / konsol.
def _strip_env(s: str | None) -> str:
    return (s or "").strip().strip('"').strip("'")


SMTP2GO_API_KEY = _strip_env(os.getenv("SMTP2GO_API_KEY"))
SMTP2GO_FROM_EMAIL = _strip_env(os.getenv("SMTP2GO_FROM_EMAIL"))
SMTP2GO_API_URL = _strip_env(os.getenv("SMTP2GO_API_URL")) or "https://api.smtp2go.com/v3/email/send"

EMAIL_HOST = (os.getenv("EMAIL_HOST") or "").strip()
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = (os.getenv("EMAIL_HOST_USER") or "").strip()
EMAIL_HOST_PASSWORD = (os.getenv("EMAIL_HOST_PASSWORD") or "").strip()
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "False") == "True"

# Markalı e-postalar: site linki (footer). Logo ``core/email_assets/centifi-logo-email.png`` (inline CID).
EMAIL_APP_URL = _strip_env(os.getenv("EMAIL_APP_URL")) or "https://centifi.app"

# Website feedback form → inbox (comma-separated for multiple recipients).
FEEDBACK_TO_EMAIL = _strip_env(os.getenv("FEEDBACK_TO_EMAIL")) or "info@centifi.app"
FEEDBACK_THROTTLE_RATE = _strip_env(os.getenv("FEEDBACK_THROTTLE_RATE")) or "10/hour"

# Website test-user signup form
TEST_USERS_TO_EMAIL = _strip_env(os.getenv("TEST_USERS_TO_EMAIL")) or FEEDBACK_TO_EMAIL
TEST_USERS_THROTTLE_RATE = _strip_env(os.getenv("TEST_USERS_THROTTLE_RATE")) or "10/hour"
# Test-user invite emails (admin → Send invite email)
TEST_USER_IOS_INVITE_URL = _strip_env(os.getenv("TEST_USER_IOS_INVITE_URL"))
TEST_USER_ANDROID_INVITE_URL = _strip_env(os.getenv("TEST_USER_ANDROID_INVITE_URL"))

# Şifre sıfırlama: e-postada 6 haneli kod; uygulamada ``/(auth)/reset-password``. ``/open/reset-password/`` sadece eski bağlantılar için bilgi sayfası.

if SMTP2GO_API_KEY and SMTP2GO_FROM_EMAIL:
    EMAIL_BACKEND = "core.mail_smtp2go.Smtp2goApiEmailBackend"
    DEFAULT_FROM_EMAIL = SMTP2GO_FROM_EMAIL
else:
    EMAIL_BACKEND = os.getenv(
        "EMAIL_BACKEND",
        "django.core.mail.backends.console.EmailBackend",
    )
    DEFAULT_FROM_EMAIL = (os.getenv("DEFAULT_FROM_EMAIL") or "webmaster@localhost").strip()

# ── AI ────────────────────────────────────────────────────────────────────────
GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY") or "").strip()

# ── Railway Bucket (S3-compatible) ────────────────────────────────────────────
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME", "")
AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", "auto")
AWS_S3_ENDPOINT_URL = os.getenv("AWS_S3_ENDPOINT_URL", "")
AWS_S3_CUSTOM_DOMAIN = os.getenv("AWS_S3_CUSTOM_DOMAIN", "") or None
AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}
AWS_DEFAULT_ACL = "public-read"
AWS_QUERYSTRING_AUTH = False

if AWS_ACCESS_KEY_ID and AWS_STORAGE_BUCKET_NAME:
    STORAGES = {
        "default": {"BACKEND": "storages.backends.s3boto3.S3Boto3Storage"},
        "staticfiles": _WHITENOISE_STATICFILES,
    }
else:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": _WHITENOISE_STATICFILES,
    }

# ── Celery (tekrarlayan masraf) ───────────────────────────────────────────────
# Broker: Redis (CELERY_BROKER_URL veya REDIS_URL). Prod’da tek konteyner: docker-entrypoint.sh
# RUN_CELERY_IN_WEB=1 ile worker + beat arka planda aynı serviste başlar (ayrı Celery servisi şart değil).
# Yerelde sadece gunicorn: RUN_CELERY_IN_WEB boş. Redis yoksa: `python manage.py process_recurring` (cron).
from celery.schedules import crontab

CELERY_BROKER_URL = (os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL") or "redis://127.0.0.1:6379/0").strip()
CELERY_RESULT_BACKEND = (os.getenv("CELERY_RESULT_BACKEND") or CELERY_BROKER_URL).strip()
CELERY_TASK_ALWAYS_EAGER = os.getenv("CELERY_TASK_ALWAYS_EAGER", "False") == "True"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "process-recurring-expenses-daily": {
        "task": "expenses.tasks.process_recurring_expenses",
        "schedule": crontab(minute=10, hour=4),
    },
}

# Worker bellek: varsayılan prefork tüm CPU’larda child açar (kolayca 2–3 GB+).
# docker-entrypoint varsayılanı `solo` tek süreç; yoğunluk için prefork + düşük concurrency kullanın.
CELERY_WORKER_PREFETCH_MULTIPLIER = int(os.getenv("CELERY_WORKER_PREFETCH_MULTIPLIER", "1"))
CELERY_WORKER_CONCURRENCY = int(os.getenv("CELERY_WORKER_CONCURRENCY", "1"))
CELERY_WORKER_MAX_TASKS_PER_CHILD = int(os.getenv("CELERY_WORKER_MAX_TASKS_PER_CHILD", "50"))

# ── Django Jazzmin (admin UI) ─────────────────────────────────────────────────
JAZZMIN_SETTINGS = {
    "site_title": "Centifi Admin",
    "site_header": "Centifi",
    "site_brand": "Centifi",
    "site_url": EMAIL_APP_URL,
    "welcome_sign": "Centifi administration",
    "copyright": "Centifi",
    "search_model": ["users.User"],
    "user_avatar": None,
    "topmenu_links": [
        {"name": "Website", "url": EMAIL_APP_URL, "new_window": True},
        {"app": "users"},
    ],
    "usermenu_links": [
        {"name": "Website", "url": EMAIL_APP_URL, "new_window": True},
    ],
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": [],
    "hide_models": [],
    "order_with_respect_to": ["users", "expenses", "ai", "django_celery_beat"],
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.group": "fas fa-users",
        "users.user": "fas fa-user-circle",
        "users.sitefeedback": "fas fa-comment-dots",
        "users.testuserapplication": "fas fa-flask",
        "users.userbankapp": "fas fa-university",
        "users.passwordresetotp": "fas fa-key",
        "expenses.expense": "fas fa-receipt",
        "expenses.expenselist": "fas fa-list",
        "expenses.usercustomcategory": "fas fa-tags",
        "expenses.recurringexpense": "fas fa-redo",
        "django_celery_beat": "fas fa-clock",
    },
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
    "related_modal_active": True,
    "changeform_format": "horizontal_tabs",
    "changeform_format_overrides": {
        "users.user": "collapsible",
    },
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": True,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-primary",
    "accent": "accent-primary",
    "navbar": "navbar-dark navbar-primary",
    "no_navbar_border": False,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "default",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success",
    },
}
