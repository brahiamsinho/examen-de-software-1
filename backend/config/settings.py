"""
Django settings for the config project.

Every environment-specific value (secrets, hosts, database credentials,
CORS origins) is read from environment variables via django-environ.
Nothing here is hardcoded, and there is no fallback to `localhost` for
the database host: in Docker Compose the Postgres service is reachable
by its service name (`db`), never `localhost`.
"""
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)

# Reads a real .env file if present (used for local/non-Docker runs);
# in Docker Compose, variables are already injected via `env_file:` /
# `.env`, so a missing file here is not an error.
environ.Env.read_env(BASE_DIR / ".env")

# --- Core -------------------------------------------------------------

SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

# --- Applications -------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    # daphne must be listed before django.contrib.staticfiles per Channels docs.
    "daphne",
    "django.contrib.staticfiles",
    # Third-party
    "channels",
    "corsheaders",
    # Local (future feature apps live under backend/apps/)
    "apps.uml_modeling",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # must sit before CommonMiddleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --- Database -------------------------------------------------------------
# Built from discrete POSTGRES_* env vars (matching the docker-compose `db`
# service) rather than a single DATABASE_URL, so the same variable names are
# shared with the `db` service definition in docker-compose.yml.

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB"),
        "USER": env("POSTGRES_USER"),
        "PASSWORD": env("POSTGRES_PASSWORD"),
        # "db" is the docker-compose service name for Postgres, NEVER localhost.
        "HOST": env("POSTGRES_HOST", default="db"),
        "PORT": env("POSTGRES_PORT", default="5432"),
    }
}

# --- Password validation ----------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Argon2 is the recommended/strongest hasher; PBKDF2 (Django's default) is kept
# as a fallback so existing PBKDF2-hashed passwords still verify.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

# --- i18n / tz ----------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# --- Static files ---------------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- CORS -------------------------------------------------------------
# The Next.js frontend runs on a different origin, so its URL(s) must be
# explicitly allow-listed via the CORS_ALLOWED_ORIGINS env var.

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
