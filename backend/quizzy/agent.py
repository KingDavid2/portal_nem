"""Local Cursor Composer agent for the Quizzy DEBUG chat stub.

Uses ``cursor-sdk`` against model ``composer-2.5`` (or ``QUIZZY_CURSOR_MODEL``).
This is an agent runtime — not a chat-completions API — so the view stays
DEBUG-only and the first-turn prompt asks the model not to mutate files.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from cursor_sdk import Agent, AgentOptions, CursorAgentError, LocalAgentOptions

FIRST_TURN_PREFIX = (
    "Eres Quizzy, asistente de planeación NEM/ABPC. Responde en español. "
    "No edites, crees ni borres archivos del repositorio; solo responde con texto.\n\n"
    "Pregunta del docente:\n"
)


@dataclass(frozen=True)
class ChatReply:
    reply: str
    agent_id: str
    model: str


class QuizzyAgentError(Exception):
    """Translated agent failure for the HTTP layer."""

    def __init__(self, message: str, *, retryable: bool = False, status: int = 502):
        super().__init__(message)
        self.message = message
        self.retryable = retryable
        self.status = status


def _local_options() -> LocalAgentOptions:
    return LocalAgentOptions(cwd=str(settings.QUIZZY_CURSOR_CWD))


def _model() -> str:
    return settings.QUIZZY_CURSOR_MODEL


def run_chat(*, message: str, agent_id: str | None, api_key: str) -> ChatReply:
    """Create or resume a local Composer agent and return its text reply."""
    model = _model()
    prompt = f"{FIRST_TURN_PREFIX}{message}" if not agent_id else message
    try:
        if agent_id:
            ctx = Agent.resume(
                agent_id,
                AgentOptions(
                    api_key=api_key,
                    model=model,
                    local=_local_options(),
                ),
            )
        else:
            ctx = Agent.create(
                model=model,
                api_key=api_key,
                local=_local_options(),
            )
        with ctx as agent:
            run = agent.send(prompt)
            result = run.wait()
            if result.status != "finished":
                raise QuizzyAgentError(
                    "Composer no pudo completar la respuesta.",
                    retryable=False,
                    status=502,
                )
            text = (result.result or "").strip()
            if not text:
                raise QuizzyAgentError(
                    "Composer devolvió una respuesta vacía.",
                    retryable=False,
                    status=502,
                )
            return ChatReply(
                reply=text,
                agent_id=agent.agent_id,
                model=model,
            )
    except QuizzyAgentError:
        raise
    except CursorAgentError as exc:
        status = 503 if exc.status in (401, 403) or "api key" in exc.message.lower() else 502
        raise QuizzyAgentError(
            exc.message,
            retryable=exc.is_retryable,
            status=status,
        ) from exc
