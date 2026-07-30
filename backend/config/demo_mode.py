"""Demo mode toggle (port of paysys/crm lib/demo_mode.rb).

In-house demo environments: set DEMO_MODE=true when DEBUG is on.
With demo mode enabled, a guest lands on a persona picker that provisions
a seeded demo workspace on demand.

  DEMO_MODE=true python manage.py runserver

For a hardened public host, set DEMO_MODE=true DEMO_DEPLOY=true with
DEBUG=false and pass validate_deploy_hardening (called from settings).

DEMO_MODE is forbidden when DEBUG is off and DEMO_DEPLOY is off —
validate() aborts boot so the unauthenticated provisioning endpoints can
never leak into an unhardened production process.
"""

from __future__ import annotations

import os
from typing import Any

from django.conf import settings

_DEFAULT_SECRET_KEY = "django-insecure-dev-only-do-not-use-in-production"
_DEFAULT_ALLOWED_HOSTS = frozenset({"localhost", "127.0.0.1"})
_REDIS_CACHE_BACKEND = "django.core.cache.backends.redis.RedisCache"


class ProductionNotAllowed(RuntimeError):
    """Raised at boot time when DEMO_MODE is set but DEBUG is off."""


class DebugNotAllowedInDemoDeploy(RuntimeError):
    """Raised at boot when DEMO_DEPLOY is on while DEBUG is still True."""


class DemoDeployNotHardened(RuntimeError):
    """Raised at boot when DEMO_DEPLOY is on but hosting posture is unsafe."""


def demo_mode_requested() -> bool:
    """Return True when the DEMO_MODE env var reads as a truthy value.

    Casts the raw environment string using the same convention as
    ActiveModel::Type::Boolean: truthy for ``true``, ``1``, ``yes``, ``on``
    (case-insensitive); falsy for ``false``, ``0``, ``no``, ``off``, empty,
    or unset.
    """
    raw = os.environ.get("DEMO_MODE", "")
    return raw.lower() in ("true", "1", "yes", "on")


def validate() -> None:
    """Raise ProductionNotAllowed when demo mode requested on a non-debug deploy.

    This is the boot guard — called from ``settings.py`` immediately after
    ``DEBUG`` is resolved. A plain raise with no try/except ensures the
    process aborts rather than degrading silently.

    When ``DEMO_DEPLOY`` is on, settings skips this call and runs
    ``validate_deploy_hardening`` at the tail instead.
    """
    if not settings.DEBUG and demo_mode_requested():
        raise ProductionNotAllowed("DEMO_MODE cannot be enabled when DEBUG is off")


def validate_deploy_hardening(
    *,
    debug: bool,
    allowed_hosts: list[str],
    secret_key: str,
    caches: dict[str, Any],
    session_cookie_secure: bool,
    csrf_cookie_secure: bool,
    demo_mode: bool,
) -> None:
    """Reject unsafe DEMO_DEPLOY hosting posture.

    Pure: every value is passed explicitly from the tail of settings.py so
    the function never reads django.conf.settings. Call only when
    DEMO_DEPLOY is True.
    """
    if debug:
        raise DebugNotAllowedInDemoDeploy(
            "DEMO_DEPLOY cannot be enabled when DEBUG is on"
        )

    if not demo_mode:
        raise DemoDeployNotHardened(
            "DEMO_DEPLOY requires DEMO_MODE so the demo surface is mounted"
        )

    if secret_key == _DEFAULT_SECRET_KEY:
        raise DemoDeployNotHardened(
            "DEMO_DEPLOY requires a non-default DJANGO_SECRET_KEY"
        )

    hosts = list(allowed_hosts)
    if "*" in hosts or set(hosts) == _DEFAULT_ALLOWED_HOSTS:
        raise DemoDeployNotHardened(
            "DEMO_DEPLOY requires explicit ALLOWED_HOSTS "
            "(not '*' and not the localhost default)"
        )

    backend = (caches.get("default") or {}).get("BACKEND", "")
    if backend != _REDIS_CACHE_BACKEND:
        raise DemoDeployNotHardened(
            "DEMO_DEPLOY requires CACHES['default'] to use RedisCache"
        )

    if not session_cookie_secure:
        raise DemoDeployNotHardened(
            "DEMO_DEPLOY requires SESSION_COOKIE_SECURE=True"
        )

    if not csrf_cookie_secure:
        raise DemoDeployNotHardened(
            "DEMO_DEPLOY requires CSRF_COOKIE_SECURE=True"
        )


def enabled() -> bool:
    """Return whether demo mode is actually active.

    Active when DEMO_MODE is requested and either DEBUG or DEMO_DEPLOY is on:

        DEMO_MODE ∧ (DEBUG ∨ DEMO_DEPLOY)

    When DEBUG is on, validate() still runs (defense in depth for the local
    path). When only DEMO_DEPLOY is on, the early ProductionNotAllowed guard
    is skipped at settings load and validate_deploy_hardening owns boot.
    """
    if not demo_mode_requested():
        return False

    if settings.DEBUG:
        validate()
        return True

    if getattr(settings, "DEMO_DEPLOY", False):
        return True

    return False
