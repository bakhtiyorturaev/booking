import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def env_list(name, default=""):
    return [
        value.strip()
        for value in os.getenv(name, default).split(",")
        if value.strip()
    ]


DEBUG = env_bool("DJANGO_DEBUG", True)

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-local-dev-key-change-in-production-only" if DEBUG else "",
)
if not SECRET_KEY:
    raise ValueError("DJANGO_SECRET_KEY environment variable is required in production.")

ALLOWED_HOSTS = ["*"] if DEBUG else (env_list("DJANGO_ALLOWED_HOSTS") or ["127.0.0.1", "localhost"])
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS") or [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", not DEBUG)
SESSION_COOKIE_SECURE = env_bool("DJANGO_SESSION_COOKIE_SECURE", not DEBUG)
CSRF_COOKIE_SECURE = env_bool("DJANGO_CSRF_COOKIE_SECURE", not DEBUG)
SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS",
    False,
)
SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD", False)
if env_bool("DJANGO_USE_X_FORWARDED_PROTO", False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
AUDIT_ASYNC = env_bool("DJANGO_AUDIT_ASYNC", True)

INSTALLED_APPS = [
    #"admin_interface",
    #"colorfield",
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "corsheaders",

    "apps.accounts.apps.AccountsConfig",
    "apps.clubs.apps.ClubsConfig",
    "apps.barbers.apps.BarbersConfig",
    "apps.bookings.apps.BookingsConfig",
    "apps.payments.apps.PaymentsConfig",
    "apps.reviews.apps.ReviewsConfig",
    "apps.audit.apps.AuditConfig",
    "apps.core.apps.CoreConfig",
    "apps.developer_bot.apps.DeveloperBotConfig",
    "telegram_bot.apps.TelegramBotConfig",
]

X_FRAME_OPTIONS = "SAMEORIGIN"
SILENCED_SYSTEM_CHECKS = ["security.W019"]

CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000",
)
CORS_ALLOW_CREDENTIALS = True
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = env_bool("CORS_ALLOW_ALL_ORIGINS", True)

SITE_ID = 1
PAYMENT_PROVIDER = os.getenv(
    "PAYMENT_PROVIDER",
    "manual" if DEBUG else "http",
).strip().lower()
PAYMENT_API_URL = os.getenv("PAYMENT_API_URL", "").strip()
PAYMENT_API_TOKEN = os.getenv("PAYMENT_API_TOKEN", "").strip()
PAYMENT_API_TIMEOUT_SECONDS = int(os.getenv("PAYMENT_API_TIMEOUT_SECONDS", "10"))
PAYMENT_WEBHOOK_SECRET = os.getenv("PAYMENT_WEBHOOK_SECRET", "").strip()
PAYMENT_CALLBACK_URL = os.getenv("PAYMENT_CALLBACK_URL", "").strip()
PAYMENT_RETURN_URL = os.getenv("PAYMENT_RETURN_URL", "").strip()
TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY", "")
TRUSTED_PROXY_IPS = {
    value.strip()
    for value in os.getenv("TRUSTED_PROXY_IPS", "127.0.0.1,::1").split(",")
    if value.strip()
}


MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "apps.audit.middleware.AuditMiddleware",

]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

if os.getenv("DB_ENGINE") == "postgresql":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "club_booking"),
            "USER": os.getenv("DB_USER", "club_booking"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "127.0.0.1"),
            "PORT": os.getenv("DB_PORT", "5432"),
            "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
            "CONN_HEALTH_CHECKS": True,
            "OPTIONS": {"connect_timeout": 5},
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

REST_FRAMEWORK = {
    "NUM_PROXIES": int(os.getenv("API_NUM_PROXIES", "1")),
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.accounts.authentication.SessionJWTAuthentication",
    ),
    "DEFAULT_SCHEMA_CLASS": (
        "drf_spectacular.openapi.AutoSchema"
    ),
    "EXCEPTION_HANDLER": "apps.clubs.exceptions.localized_api_exception_handler",
    "DEFAULT_THROTTLE_RATES": {
        "telegram_login": "20/minute",
        "token_refresh": "30/minute",
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Club Booking API",
    "DESCRIPTION": (
        "Club Booking loyihasining API hujjatlari. "
        "Himoyalangan endpointlarni sinash uchun Swagger UI dagi "
        "Authorize tugmasiga access tokenni kiriting."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "ENUM_NAME_OVERRIDES": {
        "ClubStatusEnum": "apps.clubs.models.Club.Status",
        "BranchStatusEnum": "apps.clubs.models.Branch.Status",
        "ResourceStatusEnum": "apps.clubs.models.Zone.Status",
        "ResourceTypeEnum": "apps.clubs.models.Zone.ResourceType",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": False,
}

REDIS_URL = os.getenv("REDIS_URL", "")
CACHES = {
    "default": {
        "BACKEND": (
            "django.core.cache.backends.redis.RedisCache"
            if REDIS_URL
            else "django.core.cache.backends.db.DatabaseCache"
        ),
        "LOCATION": REDIS_URL or "django_cache_table",
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 6,
        },
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "INFO",
        },
        "developer_telegram": {
            "class": "apps.developer_bot.logging.TelegramErrorHandler",
            "level": "ERROR",
        },
    },
    "root": {
        "handlers": ["console", "developer_telegram"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console", "developer_telegram"],
            "level": "INFO",
            "propagate": False,
        },
        "django.server": {
            "handlers": ["console", "developer_telegram"],
            "level": "INFO",
            "propagate": False,
        },
    },
}


STATIC_URL = '/static/' 
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "")
TELEGRAM_MINIAPP_URL = os.getenv("TELEGRAM_MINIAPP_URL", "http://localhost:3000")

