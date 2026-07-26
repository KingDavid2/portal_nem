"""Demo mode toggle (port of paysys/crm lib/demo_mode.rb).

In-house demo environments: set DEMO_MODE=true when DEBUG is on.
With demo mode enabled, a guest lands on a persona picker that provisions
a seeded demo workspace on demand.

  DEMO_MODE=true python manage.py runserver

DEMO_MODE is forbidden when DEBUG is off — validate() aborts boot so the
unauthenticated provisioning endpoints can never leak into production.
"""

from __future__ import annotations

import os

from django.conf import settings


class ProductionNotAllowed(RuntimeError):
    """Raised at boot time when DEMO_MODE is set but DEBUG is off."""


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
    """Raise ProductionNotAllowed when demo mode is requested on a non-debug deploy.

    This is the boot guard — called from ``settings.py`` immediately after
    ``DEBUG`` is resolved. A plain raise with no try/except ensures the
    process aborts rather than degrading silently.
    """
    if not settings.DEBUG and demo_mode_requested():
        raise ProductionNotAllowed("DEMO_MODE cannot be enabled when DEBUG is off")


def enabled() -> bool:
    """Return whether demo mode is actually active.

    Defense in depth: returns False immediately when DEBUG is off, before
    calling validate(). A caller can never turn demo mode on with DEBUG
    off, even if the boot guard was somehow bypassed.

    Order mirrors the Ruby original:
    1. Early False return if not DEBUG (like ``return false if Rails.env.production?``)
    2. Call validate()
    3. Return demo_mode_requested()
    """
    if not settings.DEBUG:
        return False

    validate()
    return demo_mode_requested()
