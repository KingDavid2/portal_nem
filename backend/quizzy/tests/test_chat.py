"""Tests for the DEBUG Quizzy ↔ Cursor Composer chat stub."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APIClient

from quizzy.agent import ChatReply, QuizzyAgentError
from workspaces.models import Membership, Workspace

pytestmark = pytest.mark.django_db

User = get_user_model()
CHAT_URL = "/api/quizzy/chat/"


@pytest.fixture
def membership():
    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    user = User.objects.create_user(email="quizzy@example.com", password="s3cret-pass")
    return Membership.objects.create(user=user, workspace=workspace, role="member")


@pytest.fixture
def client_for():
    def make(membership):
        client = APIClient()
        client.force_login(membership.user)
        client.credentials(HTTP_X_WORKSPACE_ID=str(membership.workspace_id))
        return client

    return make


def test_chat_requires_authentication():
    response = APIClient().post(CHAT_URL, {"message": "hola"}, format="json")
    assert response.status_code in (401, 403)


def test_chat_rejects_empty_message(membership, client_for, settings):
    settings.CURSOR_API_KEY = "test-key"
    response = client_for(membership).post(CHAT_URL, {"message": "   "}, format="json")
    assert response.status_code == 400


@override_settings(CURSOR_API_KEY=None)
def test_chat_missing_api_key_returns_503(membership, client_for):
    response = client_for(membership).post(
        CHAT_URL, {"message": "¿Qué es un PDA?"}, format="json"
    )
    assert response.status_code == 503
    assert "CURSOR_API_KEY" in response.data["detail"]


@override_settings(CURSOR_API_KEY="test-key", QUIZZY_CURSOR_MODEL="composer-2.5")
@patch("quizzy.views.run_chat")
def test_chat_returns_composer_reply(mock_run, membership, client_for):
    mock_run.return_value = ChatReply(
        reply="Un PDA es un aprendizaje esperado.",
        agent_id="agent-abc",
        model="composer-2.5",
    )

    response = client_for(membership).post(
        CHAT_URL, {"message": "¿Qué es un PDA?"}, format="json"
    )

    assert response.status_code == 200
    assert response.data == {
        "reply": "Un PDA es un aprendizaje esperado.",
        "agent_id": "agent-abc",
        "model": "composer-2.5",
    }
    mock_run.assert_called_once_with(
        message="¿Qué es un PDA?",
        agent_id=None,
        api_key="test-key",
    )


@override_settings(CURSOR_API_KEY="test-key")
@patch("quizzy.views.run_chat")
def test_chat_passes_agent_id_for_follow_up(mock_run, membership, client_for):
    mock_run.return_value = ChatReply(
        reply="Claro, más detalle.",
        agent_id="agent-abc",
        model="composer-2.5",
    )

    response = client_for(membership).post(
        CHAT_URL,
        {"message": "explica más", "agent_id": "agent-abc"},
        format="json",
    )

    assert response.status_code == 200
    mock_run.assert_called_once_with(
        message="explica más",
        agent_id="agent-abc",
        api_key="test-key",
    )


@override_settings(CURSOR_API_KEY="test-key")
@patch("quizzy.views.run_chat")
def test_chat_maps_agent_error(mock_run, membership, client_for):
    mock_run.side_effect = QuizzyAgentError("boom", retryable=True, status=502)

    response = client_for(membership).post(
        CHAT_URL, {"message": "hola"}, format="json"
    )

    assert response.status_code == 502
    assert response.data["detail"] == "boom"
    assert response.data["retryable"] is True
