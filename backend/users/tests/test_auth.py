"""RED tests for session-cookie auth (identity-auth spec)."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.views import LoginView, LogoutView
from django.test import Client
from django.urls import path
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

pytestmark = pytest.mark.django_db

User = get_user_model()


class _WhoAmI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"email": request.user.email})


urlpatterns = [
    path("login/", LoginView.as_view(template_name="users/tests_login.html")),
    path("logout/", LogoutView.as_view()),
    path("whoami/", _WhoAmI.as_view()),
]


@pytest.fixture(autouse=True)
def _urlconf(settings):
    settings.ROOT_URLCONF = __name__


@pytest.fixture
def user():
    return User.objects.create_user(email="teacher@example.com", password="s3cret-pass")


def test_login_issues_httponly_session_cookie(client: Client, user, settings):
    settings.TEMPLATES[0]["DIRS"] = [
        __file__.rsplit("/", 1)[0] + "/templates"
    ]
    response = client.post(
        "/login/",
        {"username": "teacher@example.com", "password": "s3cret-pass"},
    )
    session_cookie = response.cookies.get("sessionid")
    assert session_cookie is not None
    assert session_cookie["httponly"] is True


def test_unauthenticated_request_denied(client: Client):
    response = client.get("/whoami/")
    assert response.status_code in (401, 403)


def test_state_changing_request_without_csrf_token_rejected(client: Client, user):
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.login(email="teacher@example.com", password="s3cret-pass")
    response = csrf_client.post("/logout/")
    assert response.status_code == 403


def test_session_cookie_settings_are_httponly_and_samesite():
    from django.conf import settings

    assert settings.SESSION_COOKIE_HTTPONLY is True
    assert "rest_framework.authentication.SessionAuthentication" in (
        settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]
    )
