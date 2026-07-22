"""
Django settings for the portal_nem backend (config project).

For more information on this file, see
https://docs.djangoproject.com/en/6.0/topics/settings/
"""

from pathlib import Path

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)
# backend/.env is isolated from the repo-root .env (which holds unrelated
# M0/M1 spike secrets such as LLM API keys) to avoid DATABASE_URL collisions.
environ.Env.read_env(BASE_DIR / ".env")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="django-insecure-dev-only-do-not-use-in-production",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG", default=True)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "core",
    "users",
    "workspaces",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "workspaces.middleware.TenancyMiddleware",
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


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases
#
# Two-role split (design D-4): migrations/DDL run as the Postgres OWNER role
# (superuser locally via Postgres.app trust auth). Runtime request traffic is
# meant to connect as the restricted `portal_app` role (NOSUPERUSER
# NOBYPASSRLS), created in D8 once RLS policies exist. Until D8 lands, both
# `DJANGO_DB_ROLE=migrate` (default) and `DJANGO_DB_ROLE=runtime` resolve to
# the same owner DATABASE_URL — swapping in APP_DATABASE_URL for `runtime`
# requires no further settings restructuring.

DJANGO_DB_ROLE = env("DJANGO_DB_ROLE", default="migrate")

DATABASE_URL = env.db_url(
    "DATABASE_URL",
    default="postgres:///portal_nem",
)
APP_DATABASE_URL = (
    env.db_url("APP_DATABASE_URL") if "APP_DATABASE_URL" in env.ENVIRON else None
)

DATABASES = {
    "default": (
        APP_DATABASE_URL
        if DJANGO_DB_ROLE == "runtime" and APP_DATABASE_URL
        else DATABASE_URL
    )
}

# Every request runs inside its own transaction; the D3/D7 tenancy middleware
# relies on this to issue `SET LOCAL app.workspace_id` safely under pooling.
DATABASES["default"]["ATOMIC_REQUESTS"] = True

# Custom email-identified user (identity-auth spec). MUST be set before the
# first migration runs — AUTH_USER_MODEL is irreversible once migrated
# (design D-2 Migration/Rollout). Greenfield DB: dropped and re-migrated here
# to enforce that ordering after D1 applied the stock auth.User migration.
AUTH_USER_MODEL = "users.User"


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Django REST Framework
# https://www.django-rest-framework.org/api-guide/settings/

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "portal_nem API",
    "DESCRIPTION": "Administrative school platform for Mexico (NEM).",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# Session cookie / CSRF (identity-auth spec: httpOnly session cookie, no
# client-readable token; CSRF protection enabled via CsrfViewMiddleware above).
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # CSRF cookie must stay JS-readable for the SPA to echo it back as a header
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
