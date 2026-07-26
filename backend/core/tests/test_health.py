import os
from unittest.mock import patch

from django.test import override_settings
from rest_framework.test import APIClient

from core.views import APP_VERSION


def _without_demo_mode() -> dict[str, str]:
    """Ambient DEMO_MODE must not steer these assertions (no conftest.py here)."""
    return {key: value for key, value in os.environ.items() if key != "DEMO_MODE"}


def test_health_anonymous_returns_200_with_expected_body():
    client = APIClient()

    with patch.dict(os.environ, _without_demo_mode(), clear=True):
        response = client.get("/api/health/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": APP_VERSION,
        "demo_mode": False,
    }


def test_health_anonymous_is_not_unauthorized_or_forbidden():
    client = APIClient()

    response = client.get("/api/health/")

    assert response.status_code not in (401, 403)


def test_health_authenticated_also_returns_200_with_same_body_shape():
    client = APIClient()
    client.force_authenticate(user=object())

    with patch.dict(os.environ, _without_demo_mode(), clear=True):
        response = client.get("/api/health/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": APP_VERSION,
        "demo_mode": False,
    }


def test_health_reports_demo_mode_true_when_enabled():
    """The frontend reads this flag to decide whether to route guests to /demo."""
    client = APIClient()

    with override_settings(DEBUG=True):
        with patch.dict(os.environ, {"DEMO_MODE": "true"}):
            response = client.get("/api/health/")

    assert response.json()["demo_mode"] is True
