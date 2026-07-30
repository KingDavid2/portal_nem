"""
Django settings for the portal_nem backend (config project).

For more information on this file, see
https://docs.djangoproject.com/en/6.0/topics/settings/
"""

import os
from pathlib import Path

import environ
from corsheaders.defaults import default_headers

from config.env import load_env_files

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)
# backend/.env layered over the repo-root .env: the root file holds the LLM /
# embeddings endpoints and the generation quota, and backend/.env overrides any
# key it also declares. See `config.env` for the full precedence rules.
load_env_files(BASE_DIR)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="django-insecure-dev-only-do-not-use-in-production",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG", default=True)

# Hardened public demo host (Quizzy P6). When True, demo routes may mount
# with DEBUG=False; validate_deploy_hardening at the tail of this file owns
# the boot gate. When False, the classic ProductionNotAllowed guard below
# still rejects DEMO_MODE with DEBUG off.
DEMO_DEPLOY = env.bool("DEMO_DEPLOY", default=False)

# Boot guard: refuse to start if DEMO_MODE is set while DEBUG is off.
# DEMO_MODE creates real users via an unauthenticated endpoint; this
# aborts the process rather than degrading silently. Skipped under
# DEMO_DEPLOY — the deploy hardening validator runs after CACHES/cookies
# are resolved (see tail of this file).
from config.demo_mode import validate as _demo_mode_validate  # noqa: E402

if not DEMO_DEPLOY:
    _demo_mode_validate()

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
    "corsheaders",
    "core",
    "users",
    "workspaces",
    "schools",
    "students",
    "lesson_plans",
    "demo",
    "mcp_server",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
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
    # Per-view ScopedRateThrottle rates (no DEFAULT_THROTTLE_CLASSES — zero
    # blast radius on untouched endpoints). Quizzy P6 Slice 1a/1b scopes.
    "DEFAULT_THROTTLE_RATES": {
        "demo_personas": "60/hour",
        "demo_session_create": "5/hour",
        "demo_session_poll": "120/hour",
        "lesson_plan_generate_demo": "3/hour",
        "lesson_plan_generate": "30/hour",
        "mcp_http": "60/min",
    },
}

# Shared cache for DRF throttle counters across gunicorn/celery processes.
# Broker stays on Redis db 0; cache uses db 1 so throttle keys never collide
# with Celery messages. Under pytest, LocMem replaces Redis so CI needs no
# live broker — mirrors the CELERY_TASK_ALWAYS_EAGER block below.
REDIS_CACHE_URL = env("REDIS_CACHE_URL", default="redis://localhost:6379/1")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_CACHE_URL,
    },
}
if "PYTEST_VERSION" in os.environ:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "portal-nem-pytest",
        },
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

# CORS + CSRF trusted origins (design "same-site cookie topology (Lax
# preserved)"; tenancy-isolation spec — "Cross-Origin Credentialed Requests
# Restricted to Trusted Origins"). Frontend and backend stay on the same
# registrable domain in every environment, so SameSite=Lax cookies keep
# flowing on credentialed cross-origin fetch without moving to SameSite=None.
#
# Dev default: localhost:3000 (frontend) -> localhost:8000 (backend), no
# SESSION_COOKIE_DOMAIN (host-only cookie, port-agnostic).
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS", default=["http://localhost:3000"]
)
CORS_ALLOW_CREDENTIALS = True
# The tenancy fetch layer sends a custom `X-Workspace-Id` header on every data
# request. It is not in django-cors-headers' default allow-list, so without
# this the CORS preflight strips it and the browser blocks the request.
CORS_ALLOW_HEADERS = (*default_headers, "x-workspace-id")
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS", default=["http://localhost:3000"]
)

# Prod shape (env-gated, unset in dev): app.example.com -> api.example.com,
# shared eTLD+1 via SESSION_COOKIE_DOMAIN/CSRF_COOKIE_DOMAIN, secure cookies.
SESSION_COOKIE_DOMAIN = env("SESSION_COOKIE_DOMAIN", default=None)
CSRF_COOKIE_DOMAIN = env("CSRF_COOKIE_DOMAIN", default=None)
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=False)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=False)

# Quizzy P4 — Streamable-HTTP MCP arm. Off by default so the route is absent
# from the URLconf (404 by absence), mirroring demo_mode.enabled().
MCP_HTTP_ENABLED = env.bool("MCP_HTTP_ENABLED", default=False)
# Per-token ceiling once the arm is on (Quizzy P6 Slice 1b). Also mirrored
# under REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["mcp_http"].
MCP_HTTP_THROTTLE_RATE = env("MCP_HTTP_THROTTLE_RATE", default="60/min")

# LLM provider selection (M4 design Decision: "Provider factory reading
# LLM_PROVIDER"). `lesson_plans.core.factory.build_provider()` is the only
# reader of these settings — swapping providers never touches service/task
# code. Default targets the self-hosted vLLM (OpenAI-compatible) endpoint
# from the M1 spike; no secret is hardcoded (vLLM ignores the dummy key,
# ANTHROPIC_API_KEY has no default and must come from the environment).
LLM_PROVIDER = env("LLM_PROVIDER", default="vllm")
LLM_BASE_URL = env("LLM_BASE_URL", default="http://192.168.1.241:8000/v1")
LLM_MODEL = env("LLM_MODEL", default=None)
LLM_API_KEY = env("LLM_API_KEY", default="dummy")
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", default=None)
ANTHROPIC_MODEL = env("ANTHROPIC_MODEL", default="claude-opus-4-8")

# Eval judge (Quizzy P2). Read only by `lesson_plans.eval.judge`, and kept
# separate from ANTHROPIC_MODEL on purpose: the judge has to stay fixed while
# the *generation* model is swapped, or every previously committed scorecard
# stops being comparable to the new one.
EVAL_JUDGE_MODEL = env("EVAL_JUDGE_MODEL", default="claude-opus-5")

# Lesson-plan generation quota (design "Generaciones de este mes — 7 de 30").
# Accepted generations per workspace per calendar month, in TIME_ZONE. Read at
# call time by `lesson_plans.quota`, so overriding it needs no code change.
LESSON_PLAN_MONTHLY_GENERATION_LIMIT = env.int(
    "LESSON_PLAN_MONTHLY_GENERATION_LIMIT", default=30
)

# Demo session TTL (Quizzy P6). Expiry is derived from DemoSession.created_at —
# no migration. Beat runs the reap at most once per hour when DEMO_DEPLOY hosts
# keep celery beat alive (contractual, not enforced at boot).
DEMO_SESSION_TTL_HOURS = env.int("DEMO_SESSION_TTL_HOURS", default=24)

# Celery (M4 design — "Generation Runs Asynchronously via a Celery Task").
# Redis doubles as broker + result backend; no RabbitMQ dependency.
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env(
    "CELERY_RESULT_BACKEND", default="redis://localhost:6379/0"
)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

# Hourly beat entry for demo TTL reap. Uses celery.schedules.crontab (no
# django-celery-beat app / migration). Loaded via namespace=CELERY in
# config/celery.py.
from celery.schedules import crontab  # noqa: E402

CELERY_BEAT_SCHEDULE = {
    "reap-expired-demo-sessions": {
        "task": "demo.tasks.reap_expired_demo_sessions_task",
        "schedule": crontab(minute=0),
    },
}

# Under pytest, tasks run eagerly (synchronously, inline) so the ordinary
# service/viewset test suite never needs a live worker/broker. The
# workspace-context leak test (D4 design Decision: "Eager tasks for most
# tests, but forced non-eager for the leak test") MUST NOT rely on this —
# eager execution inherits the calling thread's contextvars and would hide
# the exact bug that requirement guards against, so that test dispatches the
# task body directly against a real (non-eager) execution path instead of
# going through `.delay()`.
if "PYTEST_VERSION" in os.environ:
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True

# DEMO_DEPLOY hosting posture (Quizzy P6 Slice 3). Runs after CACHES,
# cookies, and SPECTACULAR_SETTINGS are fully resolved so the pure
# validator receives concrete values. Forces schema-serve off and drops
# the browsable API renderer on a public demo host.
if DEMO_DEPLOY:
    from config.demo_mode import (  # noqa: E402
        demo_mode_requested as _demo_mode_requested,
        validate_deploy_hardening as _validate_deploy_hardening,
    )

    _validate_deploy_hardening(
        debug=DEBUG,
        allowed_hosts=ALLOWED_HOSTS,
        secret_key=SECRET_KEY,
        caches=CACHES,
        session_cookie_secure=SESSION_COOKIE_SECURE,
        csrf_cookie_secure=CSRF_COOKIE_SECURE,
        demo_mode=_demo_mode_requested(),
    )
    SPECTACULAR_SETTINGS["SERVE_INCLUDE_SCHEMA"] = False
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
        "rest_framework.renderers.JSONRenderer",
    ]
