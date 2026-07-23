from rest_framework.test import APIClient

from core.views import APP_VERSION


def test_health_anonymous_returns_200_with_expected_body():
    client = APIClient()

    response = client.get("/api/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": APP_VERSION}


def test_health_anonymous_is_not_unauthorized_or_forbidden():
    client = APIClient()

    response = client.get("/api/health/")

    assert response.status_code not in (401, 403)


def test_health_authenticated_also_returns_200_with_same_body_shape():
    client = APIClient()
    client.force_authenticate(user=object())

    response = client.get("/api/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": APP_VERSION}
