"""Unit tests for quizzy.agent.run_chat (Cursor SDK mocked)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from quizzy.agent import (
    FIRST_TURN_PREFIX,
    QuizzyAgentError,
    build_agent_options,
    build_first_turn_prompt,
    build_follow_up_prompt,
    run_chat,
)
from workspaces.models import Membership, Workspace

User = get_user_model()


@override_settings(QUIZZY_CURSOR_MODEL="composer-2.5", QUIZZY_CURSOR_CWD="/tmp/repo")
@patch("quizzy.agent.Agent")
def test_run_chat_creates_agent_on_first_turn(mock_agent_cls):
    agent = MagicMock()
    agent.agent_id = "agent-new"
    run = MagicMock()
    result = MagicMock(status="finished", result="Hola docente")
    run.wait.return_value = result
    agent.send.return_value = run
    mock_agent_cls.create.return_value.__enter__.return_value = agent
    mock_agent_cls.create.return_value.__exit__.return_value = None

    reply = run_chat(message="hola", agent_id=None, api_key="k")

    assert reply.reply == "Hola docente"
    assert reply.agent_id == "agent-new"
    assert reply.model == "composer-2.5"
    mock_agent_cls.create.assert_called_once()
    options = mock_agent_cls.create.call_args.args[0]
    assert options.local.custom_tools is None
    agent.send.assert_called_once()
    sent = agent.send.call_args.args[0]
    assert sent.startswith(FIRST_TURN_PREFIX)
    assert "Pregunta del docente:\nhola" in sent


@override_settings(QUIZZY_CURSOR_MODEL="composer-2.5", QUIZZY_CURSOR_CWD="/tmp/repo")
@patch("quizzy.agent.Agent")
def test_run_chat_resumes_for_follow_up(mock_agent_cls):
    agent = MagicMock()
    agent.agent_id = "agent-old"
    run = MagicMock()
    run.wait.return_value = MagicMock(status="finished", result="Seguimos")
    agent.send.return_value = run
    mock_agent_cls.resume.return_value.__enter__.return_value = agent
    mock_agent_cls.resume.return_value.__exit__.return_value = None

    reply = run_chat(message="más", agent_id="agent-old", api_key="k")

    assert reply.reply == "Seguimos"
    mock_agent_cls.resume.assert_called_once()
    agent.send.assert_called_once_with("más")


@override_settings(QUIZZY_CURSOR_MODEL="composer-2.5", QUIZZY_CURSOR_CWD="/tmp/repo")
@patch("quizzy.agent.Agent")
def test_run_chat_raises_on_failed_status(mock_agent_cls):
    agent = MagicMock()
    agent.agent_id = "agent-x"
    run = MagicMock()
    run.wait.return_value = MagicMock(status="error", result="")
    agent.send.return_value = run
    mock_agent_cls.create.return_value.__enter__.return_value = agent
    mock_agent_cls.create.return_value.__exit__.return_value = None

    with pytest.raises(QuizzyAgentError) as exc:
        run_chat(message="hola", agent_id=None, api_key="k")
    assert exc.value.status == 502


@override_settings(
    QUIZZY_CURSOR_MODEL="composer-2.5",
    QUIZZY_CURSOR_CWD="/tmp/repo",
)
@pytest.mark.django_db(transaction=True)
@patch("quizzy.agent.Agent")
def test_run_chat_with_membership_attaches_custom_tools(mock_agent_cls):
    workspace = Workspace.objects.create(type=Workspace.Type.PERSONAL)
    user = User.objects.create_user(email="quizzy-mcp@example.com", password="x")
    membership = Membership.objects.create(
        user=user, workspace=workspace, role=Membership.Role.OWNER
    )

    agent = MagicMock()
    agent.agent_id = "agent-mcp"
    run = MagicMock()
    run.wait.return_value = MagicMock(status="finished", result="Listo")
    agent.send.return_value = run
    ctx = MagicMock()
    ctx.__enter__.return_value = agent
    ctx.__exit__.return_value = None

    def _create(options):
        tools = options.local.custom_tools
        assert tools is not None
        assert "create_student" in tools
        assert "get_teaching_context" in tools
        return ctx

    mock_agent_cls.create.side_effect = _create

    reply = run_chat(
        message="Agrega a Pepe",
        agent_id=None,
        api_key="k",
        membership=membership,
    )
    assert reply.reply == "Listo"


@pytest.mark.django_db(transaction=True)
def test_custom_tool_create_student_persists():
    from cursor_sdk import CustomToolContext
    from schools.models import Group, School, SchoolYear
    from students.models import Student
    from workspaces.scope import workspace_scope

    from quizzy.custom_tools import build_portal_custom_tools

    workspace = Workspace.objects.create(type=Workspace.Type.PERSONAL)
    user = User.objects.create_user(email="tool-create@example.com", password="x")
    membership = Membership.objects.create(
        user=user, workspace=workspace, role=Membership.Role.OWNER
    )
    school = School.objects.create(
        workspace=workspace, name="E", level=School.Level.SECUNDARIA
    )
    year = SchoolYear.objects.create(
        workspace=workspace, school=school, label="2025-2026"
    )
    group = Group.objects.create(
        workspace=workspace, school_year=year, grado=1, grupo="A"
    )

    tools = build_portal_custom_tools(membership)
    out = tools["create_student"].execute(
        {
            "first_name": "Pepe",
            "last_name_paternal": "Pérez",
            "last_name_maternal": "Martínez",
        },
        CustomToolContext(),
    )
    assert out["ok"] is True
    assert out["result"]["first_name"] == "Pepe"
    assert out["result"]["school_year_label"] == "2025-2026"
    assert out["result"]["group"] == group.pk
    # cursor_sdk json.dumps the response — workspace UUID must already be a str.
    assert isinstance(out["result"]["workspace"], str)
    import json

    json.dumps(out)

    with workspace_scope(workspace.id):
        assert Student.objects.filter(
            first_name="Pepe", last_name_paternal="Pérez"
        ).exists()


@pytest.mark.django_db(transaction=True)
def test_custom_tool_teaching_context_is_json_serializable():
    import json

    from cursor_sdk import CustomToolContext
    from schools.models import Group, School, SchoolYear

    from quizzy.custom_tools import build_portal_custom_tools

    workspace = Workspace.objects.create(type=Workspace.Type.PERSONAL)
    user = User.objects.create_user(email="tool-ctx@example.com", password="x")
    membership = Membership.objects.create(
        user=user, workspace=workspace, role=Membership.Role.OWNER
    )
    school = School.objects.create(
        workspace=workspace, name="E", level=School.Level.SECUNDARIA
    )
    year = SchoolYear.objects.create(
        workspace=workspace, school=school, label="2025-2026"
    )
    Group.objects.create(workspace=workspace, school_year=year, grado=1, grupo="A")

    out = build_portal_custom_tools(membership)["get_teaching_context"].execute(
        {}, CustomToolContext()
    )
    assert out["ok"] is True
    json.dumps(out)  # must not raise on UUID workspace fields


def test_build_agent_options_without_membership_has_no_tools():
    options = build_agent_options(api_key="k", model="composer-2.5", membership=None)
    assert options.local.custom_tools is None


@pytest.mark.django_db(transaction=True)
def test_first_turn_prompt_injects_last_cycle_context():
    from schools.models import Group, School, SchoolYear

    workspace = Workspace.objects.create(type=Workspace.Type.PERSONAL)
    user = User.objects.create_user(email="ctx@example.com", password="x")
    membership = Membership.objects.create(
        user=user, workspace=workspace, role=Membership.Role.OWNER
    )
    school = School.objects.create(
        workspace=workspace, name="E", level=School.Level.SECUNDARIA
    )
    SchoolYear.objects.create(workspace=workspace, school=school, label="2022-2023")
    year = SchoolYear.objects.create(
        workspace=workspace, school=school, label="2025-2026"
    )
    Group.objects.create(
        workspace=workspace, school_year=year, grado=1, grupo="A"
    )

    prompt = build_first_turn_prompt(message="Agrega a Pepe", membership=membership)
    assert "2025-2026" in prompt
    assert "default_group_id" in prompt
    assert "NUNCA inventes" in prompt

    follow = build_follow_up_prompt(message="¿ya está?", membership=membership)
    assert "2025-2026" in follow
    assert "create_student" in follow


@pytest.mark.django_db(transaction=True)
def test_first_turn_prompt_prefers_selected_group_id():
    from schools.models import Group, School, SchoolYear

    workspace = Workspace.objects.create(type=Workspace.Type.PERSONAL)
    user = User.objects.create_user(email="sel@example.com", password="x")
    membership = Membership.objects.create(
        user=user, workspace=workspace, role=Membership.Role.OWNER
    )
    school = School.objects.create(
        workspace=workspace, name="E", level=School.Level.SECUNDARIA
    )
    year = SchoolYear.objects.create(
        workspace=workspace, school=school, label="2025-2026"
    )
    group_a = Group.objects.create(
        workspace=workspace, school_year=year, grado=1, grupo="A"
    )
    Group.objects.create(workspace=workspace, school_year=year, grado=1, grupo="B")

    prompt = build_first_turn_prompt(
        message="Lista alumnos",
        membership=membership,
        selected_group_id=group_a.pk,
    )
    assert f"selected_group_id={group_a.pk}" in prompt
    assert '"selected_group_id"' in prompt
