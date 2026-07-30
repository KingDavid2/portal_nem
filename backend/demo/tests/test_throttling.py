"""Per-view ScopedRateThrottle ceilings on the anonymous demo surface.

Design rates (Slice 1a): personas 60/h, session create 5/h, session poll 120/h.
Scopes are independent — exhausting one must not consume another.
"""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from demo.models import DemoSession

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.urls("demo.tests.urlconf_enabled"),
]


@pytest.fixture
def client() -> APIClient:
    return APIClient()


def test_personas_returns_429_at_request_61(client):
    for i in range(60):
        response = client.get("/api/demo/personas/")
        assert response.status_code == 200, f"expected 200 on request {i + 1}"

    limited = client.get("/api/demo/personas/")

    assert limited.status_code == 429


def test_session_create_returns_429_at_request_6(client):
    for i in range(5):
        response = client.post("/api/demo/sessions/", {"persona": "teacher_minimal"})
        assert response.status_code == 202, f"expected 202 on request {i + 1}"

    before = DemoSession.objects.count()
    limited = client.post("/api/demo/sessions/", {"persona": "teacher_minimal"})

    assert limited.status_code == 429
    assert DemoSession.objects.count() == before


def test_session_poll_returns_429_at_request_121(client):
    session = DemoSession.objects.create(persona="teacher_minimal")
    url = f"/api/demo/sessions/{session.pk}/"

    for i in range(120):
        response = client.get(url)
        assert response.status_code == 200, f"expected 200 on request {i + 1}"

    limited = client.get(url)

    assert limited.status_code == 429


def test_poll_exhaustion_does_not_force_create_to_429(client):
    session = DemoSession.objects.create(persona="teacher_minimal")
    url = f"/api/demo/sessions/{session.pk}/"
    for _ in range(120):
        assert client.get(url).status_code == 200
    assert client.get(url).status_code == 429

    created = client.post("/api/demo/sessions/", {"persona": "teacher_minimal"})

    assert created.status_code == 202


def test_create_exhaustion_does_not_force_personas_to_429(client):
    for _ in range(5):
        assert (
            client.post("/api/demo/sessions/", {"persona": "teacher_minimal"}).status_code
            == 202
        )
    assert (
        client.post("/api/demo/sessions/", {"persona": "teacher_minimal"}).status_code
        == 429
    )

    personas = client.get("/api/demo/personas/")

    assert personas.status_code == 200


def test_full_provision_cycle_reaches_poll_120_without_hitting_create_counter(
    client, django_capture_on_commit_callbacks
):
    """One create + 120 polls stays under create (5/h) and at the poll ceiling."""
    with django_capture_on_commit_callbacks(execute=True):
        created = client.post("/api/demo/sessions/", {"persona": "teacher_minimal"})
    assert created.status_code == 202
    session_id = created.data["id"]
    url = f"/api/demo/sessions/{session_id}/"

    for i in range(120):
        response = client.get(url)
        assert response.status_code == 200, f"expected 200 on poll {i + 1}"

    # Create budget still has room (only one create used) — a second create works.
    second = client.post("/api/demo/sessions/", {"persona": "teacher_minimal"})
    assert second.status_code == 202

    # Poll budget is exhausted after 120 successful polls.
    assert client.get(url).status_code == 429
