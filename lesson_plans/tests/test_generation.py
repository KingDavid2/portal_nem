"""Prompt assembly: the request + fixture PDAs + ABPC skeleton must reach the model."""

from __future__ import annotations

from lesson_plans.generation import GenerationRequest, build_messages
from lesson_plans.pdas import pdas_for


def _request() -> GenerationRequest:
    return GenerationRequest(
        campo="Ética, Naturaleza y Sociedades",
        grade="SEGUNDO",
        theme="La Independencia de México",
    )


def test_build_messages_has_system_then_user():
    msgs = build_messages(_request(), pdas_for("Ética, Naturaleza y Sociedades"))
    assert [m["role"] for m in msgs] == ["system", "user"]


def test_system_prompt_encodes_abpc_skeleton():
    msgs = build_messages(_request(), pdas_for("Ética, Naturaleza y Sociedades"))
    system = msgs[0]["content"]
    assert "ABPC" in system or "APRENDIZAJE BASADO EN PROYECTOS COMUNITARIOS" in system
    assert "11" in system  # 11 momentos
    assert "Planeación" in system and "Acción" in system and "Intervención" in system


def test_user_message_embeds_request_and_every_pda_verbatim():
    groups = pdas_for("Ética, Naturaleza y Sociedades")
    user = build_messages(_request(), groups)[1]["content"]
    assert "SEGUNDO" in user
    assert "La Independencia de México" in user
    assert "Ética, Naturaleza y Sociedades" in user
    for group in groups:
        assert group.content in user
        for pda in group.pdas:
            assert pda in user
