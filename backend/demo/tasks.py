"""Celery task that provisions a demo tenant for a `DemoSession`.

Port of paysys/crm `Demo::ProvisionJob`. Provisioning cannot happen inside the
POST request: `DATABASES["default"]["ATOMIC_REQUESTS"] = True`, so the whole
view runs in one transaction and seeding a full workspace there would hold it
open for the entire duration. The view returns a `pending` receipt immediately
and this task moves it to a terminal state.

Every exit path must leave the row terminal. A guest polls this row from the
browser; a session stranded at `pending` is an eternal spinner with nothing to
show and no way to recover.
"""

from __future__ import annotations

import logging

from celery import shared_task

from demo import personas
from demo.models import DemoSession
from demo.reaping import reap_expired_demo_sessions

logger = logging.getLogger(__name__)

# Keep a verbose traceback message from blowing out the column and from being
# echoed back to an unauthenticated caller in full.
ERROR_MESSAGE_MAX_LENGTH = 2000


@shared_task
def reap_expired_demo_sessions_task() -> int:
    """Thin Celery wrapper around ``reaping.reap_expired_demo_sessions``.

    Beat schedules this hourly (see ``CELERY_BEAT_SCHEDULE``). Logic lives in
    the pure service so tests call it without a broker.
    """
    return reap_expired_demo_sessions()


@shared_task
def provision_demo_session_task(demo_session_id) -> None:
    """Provision the tenant for `demo_session_id` and record the outcome.

    Idempotent by status, exactly like `ProvisionJob`: a session that is no
    longer `pending` has already been decided — returning early is what stops
    a duplicate delivery from provisioning a second workspace, or from
    overwriting a recorded failure.

    Args:
        demo_session_id: Primary key of the `DemoSession` to provision.
    """
    session = DemoSession.objects.get(pk=demo_session_id)
    if session.status != DemoSession.Status.PENDING:
        return

    try:
        persona = personas.find(session.persona)
        user, workspace = persona.resolve_provisioner()().provision()
    except Exception as exc:
        logger.exception(
            "provision_demo_session_task failed session=%s persona=%s",
            demo_session_id,
            session.persona,
        )
        session.status = DemoSession.Status.FAILED
        session.error_message = str(exc)[:ERROR_MESSAGE_MAX_LENGTH]
        session.save(update_fields=["status", "error_message"])
        return

    session.user = user
    session.workspace = workspace
    session.status = DemoSession.Status.READY
    session.save(update_fields=["user", "workspace", "status"])
