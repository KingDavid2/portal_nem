"""Unit tests for quizzy.agent.run_chat (Cursor SDK mocked)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from quizzy.agent import FIRST_TURN_PREFIX, QuizzyAgentError, run_chat


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
    agent.send.assert_called_once_with(f"{FIRST_TURN_PREFIX}hola")


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
