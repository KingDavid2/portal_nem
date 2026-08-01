"""Local Cursor Composer agent for the Quizzy chat.

Uses ``cursor-sdk`` against model ``composer-2.5`` (or ``QUIZZY_CURSOR_MODEL``).
Tenant mutations run through in-process ``custom_tools`` bound to the MCP
``dispatch`` registry (stdio MCP alone was not being invoked — Composer
hallucinated creates).
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from cursor_sdk import Agent, AgentOptions, CursorAgentError, LocalAgentOptions
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder

from mcp_server.context import teaching_context_payload
from quizzy.custom_tools import build_portal_custom_tools
from workspaces.scope import workspace_scope

FIRST_TURN_PREFIX = (
    "Eres Quizzy, asistente de planeación NEM/ABPC para docentes. Responde en español.\n"
    "No edites archivos del repositorio. Para leer o mutar datos del tenant DEBES "
    "llamar las herramientas (create_student, list_students, get_teaching_context, …).\n\n"
    "Reglas estrictas:\n"
    "- NUNCA inventes un alta. Solo di que un alumno quedó registrado si "
    "create_student devolvió ok=true con un result.id real.\n"
    "- Si ok=false o no llamaste la herramienta, di que no se creó.\n"
    "- Último ciclo = last_school_year_label del contexto. No uses otro ciclo "
    "salvo que el docente lo nombre (entonces school_year_label).\n"
    "- Si group_count > 1 y el docente no eligió grupo, pregunta (1° A / 1° B, …) "
    "ANTES de create_student. No elijas por tu cuenta.\n"
    "- Si group_count == 1, puedes omitir group_id.\n"
    "- Ortografía: si create_student/update_student devuelve "
    "needs_clarification / needs_orthography_clarification, muestra typed vs "
    "suggested y pregunta al docente. Con su OK reintenta con "
    "apply_suggested=true (acentos) o keep_as_typed=true (dejar como escribió). "
    "No inventes la decisión.\n"
    "- Update/delete: confirma con el docente, luego confirm=true.\n"
    "- Al reportar, copia id / school_year_label / group del result de la herramienta.\n\n"
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


def _model() -> str:
    return settings.QUIZZY_CURSOR_MODEL


def _teaching_context_block(membership) -> str:
    with workspace_scope(membership.workspace_id):
        payload = teaching_context_payload()
    return (
        "Contexto del workspace (fuente de verdad; no inventes otro):\n"
        f"{json.dumps(payload, ensure_ascii=False, cls=DjangoJSONEncoder)}\n\n"
    )


def build_local_options(*, membership=None) -> LocalAgentOptions:
    kwargs: dict = {"cwd": str(settings.QUIZZY_CURSOR_CWD)}
    if membership is not None:
        kwargs["custom_tools"] = build_portal_custom_tools(membership)
    return LocalAgentOptions(**kwargs)


def build_agent_options(*, api_key: str, model: str, membership=None) -> AgentOptions:
    return AgentOptions(
        api_key=api_key,
        model=model,
        local=build_local_options(membership=membership),
    )


def build_first_turn_prompt(*, message: str, membership=None) -> str:
    prefix = FIRST_TURN_PREFIX
    if membership is not None:
        prefix = f"{FIRST_TURN_PREFIX}{_teaching_context_block(membership)}"
    return f"{prefix}Pregunta del docente:\n{message}"


def build_follow_up_prompt(*, message: str, membership=None) -> str:
    """Resume turns still get live context so the model cannot reuse invented state."""
    if membership is None:
        return message
    return (
        f"{_teaching_context_block(membership)}"
        "Recuerda: solo confirma altas si create_student devolvió ok=true. "
        "Si hay varios grupos, pregunta cuál.\n\n"
        f"Mensaje del docente:\n{message}"
    )


def run_chat(
    *,
    message: str,
    agent_id: str | None,
    api_key: str,
    membership=None,
) -> ChatReply:
    """Create or resume a local Composer agent and return its text reply."""
    model = _model()
    if agent_id:
        prompt = build_follow_up_prompt(message=message, membership=membership)
    else:
        prompt = build_first_turn_prompt(message=message, membership=membership)

    options = build_agent_options(
        api_key=api_key, model=model, membership=membership
    )
    try:
        if agent_id:
            ctx = Agent.resume(agent_id, options)
        else:
            ctx = Agent.create(options)
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
        status = (
            503
            if exc.status in (401, 403) or "api key" in exc.message.lower()
            else 502
        )
        raise QuizzyAgentError(
            exc.message,
            retryable=exc.is_retryable,
            status=status,
        ) from exc
