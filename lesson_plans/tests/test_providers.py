"""Provider contract + the deterministic PDA-fidelity guard (Phase B's detector seed).

The live instructor call is exercised at the exit gate, not here; these tests inject
the structured-completion boundary so generate()'s orchestration + guard are pinned.
"""

from __future__ import annotations

import pytest

from lesson_plans.generation import GenerationRequest
from lesson_plans.pdas import pdas_for
from lesson_plans.ports.claude import ClaudeProvider
from lesson_plans.ports.llm import Usage, find_invented_pdas
from lesson_plans.ports.openai_compat import OpenAICompatProvider
from lesson_plans.schema import (
    ContentPda,
    Datos,
    Momento,
    Proyecto,
    Rubric,
    RubricCriterion,
    Session,
    Stage,
    Step,
)

CAMPO = "Ética, Naturaleza y Sociedades"
REQUEST = GenerationRequest(campo=CAMPO, grade="SEGUNDO", theme="La Independencia de México")


def _proyecto_with(pdas: list[str]) -> Proyecto:
    return Proyecto(
        datos=Datos(school_name="X", grade="SEGUNDO", campo_formativo=CAMPO, date="HOY"),
        title="T",
        purpose="P",
        articulating_axes=[{"name": "Inclusión", "justification": "j"}],
        problem_or_theme="La Independencia de México",
        contents_and_pdas=[ContentPda(content="c", pdas=pdas)],
        stages=[
            Stage(
                name="Planeación",
                momentos=[Momento(number=1, name="Identificación", sessions=[Session(duration_minutes=30, steps=[Step(number=1, dynamic="d")])])],
            )
        ],
        rubric=Rubric(criteria=[RubricCriterion(criterion="Participación", levels=["A", "B", "C", "D"])]),
    )


def _fake_complete(proyecto: Proyecto):
    def complete(system: str, user: str):
        return proyecto, Usage(input_tokens=100, output_tokens=200)
    return complete


def test_find_invented_pdas_ignores_whitespace_and_case():
    fixture = pdas_for(CAMPO)
    faithful = [p for g in fixture for p in g.pdas]
    # Same PDA with collapsed whitespace + different case is NOT invented.
    tweaked = "  " + faithful[0].upper().replace(" ", "   ") + " "
    proyecto = _proyecto_with([tweaked])
    assert find_invented_pdas(proyecto, fixture) == []


def test_find_invented_pdas_flags_a_hallucinated_pda():
    fixture = pdas_for(CAMPO)
    proyecto = _proyecto_with(["Este PDA no existe en el corpus."])
    assert find_invented_pdas(proyecto, fixture) == ["Este PDA no existe en el corpus."]


@pytest.mark.parametrize("Provider", [ClaudeProvider, OpenAICompatProvider])
def test_generate_returns_result_with_usage_and_guard(Provider):
    fixture = pdas_for(CAMPO)
    faithful = [p for g in fixture for p in g.pdas]
    proyecto = _proyecto_with(faithful)
    provider = Provider(complete=_fake_complete(proyecto), model="m")
    result = provider.generate(REQUEST, fixture)
    assert result.proyecto is proyecto
    assert result.usage == Usage(input_tokens=100, output_tokens=200)
    assert result.invented_pdas == []
    assert provider.name in {"claude", "qwen"}
