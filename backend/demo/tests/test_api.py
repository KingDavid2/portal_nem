"""HTTP tests for the three unauthenticated demo endpoints.

Port of paysys/crm `Demo::SessionsController`: a guest lists personas, POSTs
one, gets a `pending` receipt back immediately (provisioning happens in the
Celery task), then polls the receipt until it is `ready` — at which point the
GET signs the guest in. Re-polling a ready session signs in again and never
provisions a second workspace.
"""

from __future__ import annotations

import uuid

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from demo.models import DemoSession
from workspaces.models import Workspace

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.urls("demo.tests.urlconf_enabled"),
]


@pytest.fixture
def client() -> APIClient:
    return APIClient()


def test_personas_endpoint_lists_the_registry_to_an_anonymous_caller(client):
    response = client.get("/api/demo/personas/")

    assert response.status_code == 200
    keys = [row["key"] for row in response.data]
    assert keys == ["teacher_minimal", "teacher_full", "quota_exhausted"]
    first = response.data[0]
    assert first["label"]
    assert first["description"]
    assert isinstance(first["features"], list)
    # The provisioner import path is an internal detail — never exposed.
    assert "provisioner" not in first


def test_create_session_returns_202_with_a_pending_receipt(client):
    response = client.post("/api/demo/sessions/", {"persona": "teacher_minimal"})

    assert response.status_code == 202
    assert response.data["status"] == DemoSession.Status.PENDING
    session = DemoSession.objects.get(pk=response.data["id"])
    assert session.persona == "teacher_minimal"


def test_create_session_enqueues_provisioning_after_commit(
    client, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        response = client.post("/api/demo/sessions/", {"persona": "teacher_full"})

    session = DemoSession.objects.get(pk=response.data["id"])
    assert session.status == DemoSession.Status.READY
    assert session.provisioned is True


def test_create_session_rejects_an_unknown_persona(client):
    response = client.post("/api/demo/sessions/", {"persona": "nope"})

    assert response.status_code == 400
    assert DemoSession.objects.count() == 0


def test_pending_session_reports_pending_without_signing_anyone_in(client):
    session = DemoSession.objects.create(persona="teacher_minimal")

    response = client.get(f"/api/demo/sessions/{session.pk}/")

    assert response.status_code == 200
    assert response.data["status"] == DemoSession.Status.PENDING
    assert response.data["workspace"] is None
    assert client.get("/api/auth/me/").status_code == 403


def test_failed_session_reports_the_error_message(client):
    session = DemoSession.objects.create(
        persona="teacher_minimal",
        status=DemoSession.Status.FAILED,
        error_message="no se pudo aprovisionar",
    )

    response = client.get(f"/api/demo/sessions/{session.pk}/")

    assert response.status_code == 200
    assert response.data["status"] == DemoSession.Status.FAILED
    assert response.data["error_message"] == "no se pudo aprovisionar"


def test_ready_session_signs_the_guest_in(client, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        created = client.post("/api/demo/sessions/", {"persona": "teacher_minimal"})
    session_id = created.data["id"]

    response = client.get(f"/api/demo/sessions/{session_id}/")

    assert response.status_code == 200
    assert response.data["status"] == DemoSession.Status.READY
    session = DemoSession.objects.get(pk=session_id)
    assert response.data["workspace"] == session.workspace_id
    assert response.data["email"] == session.user.email
    me = client.get("/api/auth/me/")
    assert me.status_code == 200
    assert me.data["email"] == session.user.email


def test_re_polling_a_ready_session_never_provisions_a_second_workspace(
    client, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        created = client.post("/api/demo/sessions/", {"persona": "teacher_minimal"})
    session_id = created.data["id"]
    client.get(f"/api/demo/sessions/{session_id}/")
    workspace_count = Workspace.objects.count()

    second = APIClient().get(f"/api/demo/sessions/{session_id}/")

    assert second.status_code == 200
    assert Workspace.objects.count() == workspace_count
    assert second.data["workspace"] == DemoSession.objects.get(pk=session_id).workspace_id


def test_unknown_session_id_is_404(client):
    response = client.get(f"/api/demo/sessions/{uuid.uuid4()}/")

    assert response.status_code == 404


@override_settings(DEBUG=True)
def test_endpoints_need_no_csrf_token_or_credentials():
    """A guest has neither a session nor a CSRF cookie when it first POSTs."""
    enforcing = APIClient(enforce_csrf_checks=True)

    response = enforcing.post("/api/demo/sessions/", {"persona": "teacher_minimal"})

    assert response.status_code == 202
