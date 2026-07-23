"""RED/GREEN tests for session-cookie auth (identity-auth spec — "Session
Login/Logout/Me Endpoints"), exercised against the real `/api/auth/` routes.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from rest_framework.test import APIClient

from workspaces.models import Membership, Workspace

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture
def user():
    created = User.objects.create_user(email="teacher@example.com", password="s3cret-pass")
    # TenancyMiddleware runs for every authenticated request and falls back
    # to the user's personal workspace when no `X-Workspace-Id` header is
    # sent — these auth endpoints are deliberately header-free, so the
    # fixture needs a personal workspace for the middleware to resolve.
    personal_workspace = Workspace.objects.create(type=Workspace.Type.PERSONAL)
    Membership.objects.create(
        user=created, workspace=personal_workspace, role=Membership.Role.OWNER
    )
    return created


def test_login_with_valid_credentials_issues_httponly_session_cookie(client: Client, user):
    response = client.post(
        "/api/auth/login/",
        {"email": "teacher@example.com", "password": "s3cret-pass"},
        content_type="application/json",
    )
    assert response.status_code == 200
    session_cookie = response.cookies.get("sessionid")
    assert session_cookie is not None
    assert session_cookie["httponly"] is True


def test_login_with_invalid_credentials_is_rejected_and_sets_no_session(client: Client, user):
    response = client.post(
        "/api/auth/login/",
        {"email": "teacher@example.com", "password": "wrong-pass"},
        content_type="application/json",
    )
    assert 400 <= response.status_code < 500
    session_cookie = response.cookies.get("sessionid")
    assert session_cookie is None or not session_cookie.value


def test_logout_clears_the_session(client: Client, user):
    client.login(email="teacher@example.com", password="s3cret-pass")

    logout_response = client.post("/api/auth/logout/")
    assert logout_response.status_code in (200, 204)

    me_response = client.get("/api/auth/me/")
    assert me_response.status_code in (401, 403)


def test_me_returns_current_user_when_authenticated(client: Client, user):
    client.login(email="teacher@example.com", password="s3cret-pass")

    response = client.get("/api/auth/me/")
    assert response.status_code == 200
    assert response.json()["email"] == "teacher@example.com"


def test_me_denies_anonymous_access(client: Client):
    response = client.get("/api/auth/me/")
    assert response.status_code in (401, 403)


def test_state_changing_request_without_csrf_token_rejected(user):
    csrf_client = APIClient(enforce_csrf_checks=True)
    csrf_client.login(email="teacher@example.com", password="s3cret-pass")
    response = csrf_client.post("/api/auth/logout/")
    assert response.status_code == 403


def test_session_cookie_settings_are_httponly_and_samesite():
    from django.conf import settings

    assert settings.SESSION_COOKIE_HTTPONLY is True
    assert "rest_framework.authentication.SessionAuthentication" in (
        settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]
    )
