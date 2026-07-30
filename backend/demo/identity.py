"""Demo-guest identity helpers (Quizzy P6 Slice 1b).

Authoritative check via DemoSession — no email heuristics, no migration.
"""

from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser

from demo.models import DemoSession


def is_demo_guest(user: AbstractBaseUser | None) -> bool:
    """True when ``user`` owns a READY DemoSession (provisioned demo guest)."""
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    return DemoSession.objects.filter(
        user_id=user.pk, status=DemoSession.Status.READY
    ).exists()
