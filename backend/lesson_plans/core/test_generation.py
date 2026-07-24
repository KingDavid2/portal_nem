"""Tests for prompt assembly.

Assertions are on what the model can actually read: display names rather than
catalog ids, the teacher's whole planning context, and the two rules that bind
the output to the given ejes articuladores, duration and scenario.
"""

from __future__ import annotations

import pytest

from lesson_plans.core.generation import (
    SYSTEM_PROMPT,
    GenerationRequest,
    build_messages,
    scenario_label,
)
from lesson_plans.core.schema import ContentPda


def _request(**overrides) -> GenerationRequest:
    defaults = dict(
        campo="Lenguajes",
        grade="2",
        theme="La contaminación del río",
        subject="Español",
        duration_weeks=4,
        start_date="2026-01-12",
        end_date="2026-02-09",
        scenario="Comunidad",
        context_diagnosis="El grupo lee con fluidez pero redacta con poca cohesión.",
        cross_cutting_themes=("Pensamiento crítico", "Inclusión"),
    )
    return GenerationRequest(**{**defaults, **overrides})


def _user_message(request: GenerationRequest) -> str:
    pdas = [ContentPda(content="Contenido oficial", pdas=["PDA oficial"])]
    return build_messages(request, pdas)[1]["content"]


@pytest.mark.parametrize(
    "expected",
    [
        "Español",
        "Comunidad",
        "4 semanas",
        "2026-01-12",
        "2026-02-09",
        "El grupo lee con fluidez pero redacta con poca cohesión.",
        "Pensamiento crítico, Inclusión",
        "Contenido oficial",
        "PDA oficial",
    ],
)
def test_user_message_carries_the_planning_context(expected):
    assert expected in _user_message(_request())


def test_system_prompt_binds_the_ejes_and_the_duration_and_scenario():
    assert "Usa EXCLUSIVAMENTE los ejes articuladores" in SYSTEM_PROMPT
    assert "Respeta la duración y el escenario indicados" in SYSTEM_PROMPT


def test_system_prompt_keeps_the_no_invented_pdas_rule():
    assert (
        "Usa EXCLUSIVAMENTE los contenidos y PDAs que se te proporcionan" in SYSTEM_PROMPT
    )


def test_scenario_label_renders_spanish_wording():
    assert scenario_label("community") == "Comunidad"
    assert scenario_label("classroom") == "Aula"
    assert scenario_label("school") == "Escuela"


def test_unknown_scenario_raises_key_error():
    with pytest.raises(KeyError):
        scenario_label("playground")
