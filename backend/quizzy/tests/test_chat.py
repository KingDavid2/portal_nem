"""Tests for the DEBUG Quizzy ↔ Cursor Composer chat stub + persistence."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APIClient

from quizzy.agent import ChatReply, QuizzyAgentError
from quizzy.models import Conversation, Message
from workspaces.models import Membership, Workspace
from workspaces.scope import workspace_scope

pytestmark = pytest.mark.django_db

User = get_user_model()
CHAT_URL = "/api/quizzy/chat/"
CONVERSATIONS_URL = "/api/quizzy/conversations/"


@pytest.fixture
def membership():
    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    user = User.objects.create_user(email="quizzy@example.com", password="s3cret-pass")
    return Membership.objects.create(user=user, workspace=workspace, role="member")


@pytest.fixture
def other_membership(membership):
    other_user = User.objects.create_user(
        email="other@example.com", password="s3cret-pass"
    )
    return Membership.objects.create(
        user=other_user, workspace=membership.workspace, role="member"
    )


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
@patch("quizzy.services.run_chat")
def test_chat_returns_composer_reply_and_persists(mock_run, membership, client_for):
    mock_run.return_value = ChatReply(
        reply="Un PDA es un aprendizaje esperado.",
        agent_id="agent-abc",
        model="composer-2.5",
    )

    response = client_for(membership).post(
        CHAT_URL, {"message": "¿Qué es un PDA?"}, format="json"
    )

    assert response.status_code == 200
    assert response.data["reply"] == "Un PDA es un aprendizaje esperado."
    assert response.data["agent_id"] == "agent-abc"
    assert response.data["model"] == "composer-2.5"
    assert response.data["conversation_id"]

    with workspace_scope(membership.workspace_id):
        conversation = Conversation.objects.get(pk=response.data["conversation_id"])
        assert conversation.created_by_id == membership.user_id
        assert conversation.workspace_id == membership.workspace_id
        assert conversation.title == "¿Qué es un PDA?"
        assert conversation.agent_id == "agent-abc"
        messages = list(conversation.messages.order_by("created_at"))
        assert [(m.role, m.content) for m in messages] == [
            (Message.Role.USER, "¿Qué es un PDA?"),
            (Message.Role.ASSISTANT, "Un PDA es un aprendizaje esperado."),
        ]
    mock_run.assert_called_once_with(
        message="¿Qué es un PDA?",
        agent_id=None,
        api_key="test-key",
        membership=membership,
        selected_group_id=None,
    )


@override_settings(CURSOR_API_KEY="test-key", QUIZZY_CURSOR_MODEL="composer-2.5")
@patch("quizzy.services.run_chat")
def test_chat_passes_group_id_to_run_chat(mock_run, membership, client_for):
    from schools.models import Group, School, SchoolYear

    mock_run.return_value = ChatReply(
        reply="ok",
        agent_id="agent-g",
        model="composer-2.5",
    )
    with workspace_scope(membership.workspace_id):
        school = School.objects.create(
            workspace=membership.workspace,
            name="E",
            level=School.Level.SECUNDARIA,
        )
        year = SchoolYear.objects.create(
            workspace=membership.workspace, school=school, label="2025-2026"
        )
        group = Group.objects.create(
            workspace=membership.workspace, school_year=year, grado=1, grupo="A"
        )

    response = client_for(membership).post(
        CHAT_URL,
        {"message": "hola", "group_id": group.pk},
        format="json",
    )
    assert response.status_code == 200
    assert mock_run.call_args.kwargs["selected_group_id"] == group.pk


@override_settings(CURSOR_API_KEY="test-key")
def test_chat_rejects_foreign_group_id(membership, client_for):
    response = client_for(membership).post(
        CHAT_URL,
        {"message": "hola", "group_id": 999999},
        format="json",
    )
    assert response.status_code == 400
    assert "group_id" in response.data


@override_settings(CURSOR_API_KEY="test-key")
@patch("quizzy.services.run_chat")
def test_chat_follow_up_uses_stored_agent_id(mock_run, membership, client_for):
    conversation = Conversation.objects.create(
        workspace=membership.workspace,
        created_by=membership.user,
        title="Primera",
        agent_id="agent-abc",
    )
    mock_run.return_value = ChatReply(
        reply="Claro, más detalle.",
        agent_id="agent-abc",
        model="composer-2.5",
    )

    response = client_for(membership).post(
        CHAT_URL,
        {
            "message": "explica más",
            "conversation_id": str(conversation.id),
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.data["conversation_id"] == str(conversation.id)
    mock_run.assert_called_once_with(
        message="explica más",
        agent_id="agent-abc",
        api_key="test-key",
        membership=membership,
        selected_group_id=None,
    )
    assert conversation.messages.count() == 2


@override_settings(CURSOR_API_KEY="test-key")
@patch("quizzy.services.run_chat")
def test_chat_maps_agent_error_without_persisting(mock_run, membership, client_for):
    mock_run.side_effect = QuizzyAgentError("boom", retryable=True, status=502)

    response = client_for(membership).post(
        CHAT_URL, {"message": "hola"}, format="json"
    )

    assert response.status_code == 502
    assert response.data["detail"] == "boom"
    assert response.data["retryable"] is True
    with workspace_scope(membership.workspace_id):
        assert Conversation.objects.count() == 0


@override_settings(CURSOR_API_KEY="test-key")
@patch("quizzy.services.run_chat")
def test_list_conversations_owner_only(
    mock_run, membership, other_membership, client_for
):
    mock_run.return_value = ChatReply(
        reply="ok", agent_id="a1", model="composer-2.5"
    )
    client_for(membership).post(CHAT_URL, {"message": "mía"}, format="json")
    client_for(other_membership).post(CHAT_URL, {"message": "ajena"}, format="json")

    response = client_for(membership).get(CONVERSATIONS_URL)
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["title"] == "mía"


@override_settings(CURSOR_API_KEY="test-key")
@patch("quizzy.services.run_chat")
def test_retrieve_conversation_with_messages(mock_run, membership, client_for):
    mock_run.return_value = ChatReply(
        reply="respuesta", agent_id="a1", model="composer-2.5"
    )
    create = client_for(membership).post(
        CHAT_URL, {"message": "hola"}, format="json"
    )
    conversation_id = create.data["conversation_id"]

    response = client_for(membership).get(f"{CONVERSATIONS_URL}{conversation_id}/")
    assert response.status_code == 200
    assert response.data["id"] == conversation_id
    assert len(response.data["messages"]) == 2
    assert response.data["messages"][0]["role"] == "user"
    assert response.data["messages"][1]["role"] == "assistant"


def test_retrieve_foreign_conversation_404(membership, other_membership, client_for):
    conversation = Conversation.objects.create(
        workspace=membership.workspace,
        created_by=other_membership.user,
        title="secreta",
    )
    response = client_for(membership).get(f"{CONVERSATIONS_URL}{conversation.id}/")
    assert response.status_code == 404


@override_settings(CURSOR_API_KEY="test-key")
@patch("quizzy.services.run_chat")
def test_delete_conversation(mock_run, membership, client_for):
    mock_run.return_value = ChatReply(
        reply="ok", agent_id="a1", model="composer-2.5"
    )
    create = client_for(membership).post(
        CHAT_URL, {"message": "borrar"}, format="json"
    )
    conversation_id = create.data["conversation_id"]

    response = client_for(membership).delete(f"{CONVERSATIONS_URL}{conversation_id}/")
    assert response.status_code == 204
    with workspace_scope(membership.workspace_id):
        assert not Conversation.objects.filter(pk=conversation_id).exists()


@override_settings(CURSOR_API_KEY="test-key")
@patch("quizzy.services.run_chat")
def test_rename_conversation(mock_run, membership, client_for):
    mock_run.return_value = ChatReply(
        reply="ok", agent_id="a1", model="composer-2.5"
    )
    create = client_for(membership).post(
        CHAT_URL, {"message": "título original"}, format="json"
    )
    conversation_id = create.data["conversation_id"]

    response = client_for(membership).patch(
        f"{CONVERSATIONS_URL}{conversation_id}/",
        {"title": "  Nuevo título  "},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["title"] == "Nuevo título"
    with workspace_scope(membership.workspace_id):
        assert Conversation.objects.get(pk=conversation_id).title == "Nuevo título"


def test_rename_rejects_empty_title(membership, client_for):
    conversation = Conversation.objects.create(
        workspace=membership.workspace,
        created_by=membership.user,
        title="antes",
    )
    response = client_for(membership).patch(
        f"{CONVERSATIONS_URL}{conversation.id}/",
        {"title": "   "},
        format="json",
    )
    assert response.status_code == 400
