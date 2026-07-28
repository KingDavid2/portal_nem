"""Scorecard assembly, costing, and the schema-failure probe — all token-free.

The provider and the judge are both injected, so every branch here (success,
schema failure, transient fault) is exercised without a live call.
"""

from __future__ import annotations

import pytest

from ..core.grounding import GroundingReport
from ..core.ports.llm import GenerationResult, TransientProviderError, Usage
from ..core.schema import (
    ArticulatingAxis,
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
from .cases import CASES
from .judge import Judge, JudgeScore
from .run import Row, SchemaProbe, format_scorecard, probe_schema, run_cases, usd


def _proyecto(pda: str = "PDA oficial") -> Proyecto:
    return Proyecto(
        datos=Datos(
            school_name="Escuela Secundaria General",
            grade="SEGUNDO",
            campo_formativo="ÉTICA, NATURALEZA Y SOCIEDADES",
            date="JUEVES, 18 DE SEPTIEMBRE DE 2025",
        ),
        title="Héroes y Gestas",
        purpose="Comprender los movimientos de resistencia.",
        articulating_axes=[ArticulatingAxis(name="Inclusión", justification="Integrar.")],
        problem_or_theme="La Independencia de México",
        contents_and_pdas=[ContentPda(content="Las gestas de resistencia.", pdas=[pda])],
        stages=[
            Stage(
                name="Planeación",
                momentos=[
                    Momento(
                        number=1,
                        name="Identificación",
                        sessions=[
                            Session(duration_minutes=30, steps=[Step(number=1, dynamic="Intro.")])
                        ],
                    )
                ],
            )
        ],
        rubric=Rubric(criteria=[RubricCriterion(criterion="Participación", levels=["1", "2", "3", "4"])]),
    )


class FakeProvider:
    """Stands in for an adapter: replays a scripted outcome per call."""

    name = "fake"

    def __init__(self, outcomes):
        self._outcomes = list(outcomes)
        self.calls = 0

    def generate(self, request, pdas):
        self.calls += 1
        outcome = self._outcomes[(self.calls - 1) % len(self._outcomes)]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _ok(invented: list[str] | None = None) -> GenerationResult:
    return GenerationResult(
        proyecto=_proyecto(),
        usage=Usage(input_tokens=1000, output_tokens=2000),
        invented_pdas=invented or [],
    )


def _judge(score: JudgeScore | None = None) -> Judge:
    canned = score or JudgeScore(
        pda_fidelity=5,
        structural_completeness=4,
        coherence=4,
        spanish_register=5,
        rationale="bien",
    )
    return Judge(score=lambda golden, candidate, official: canned)


# --- costing -----------------------------------------------------------------


def test_usd_prices_input_and_output_separately():
    # claude-opus-5: $5/MTok in, $25/MTok out.
    cost = usd(Usage(input_tokens=1_000_000, output_tokens=1_000_000), "claude-opus-5")
    assert cost == pytest.approx(30.0)


def test_usd_is_none_for_a_self_hosted_model():
    """Self-hosted inference is not billed per token; a fabricated dollar figure
    would be worse than no figure at all."""
    assert usd(Usage(input_tokens=1000, output_tokens=1000), "Qwen3.6-40B") is None


# --- schema-failure probe ----------------------------------------------------


def test_probe_counts_only_terminal_schema_failures():
    """`raise_provider_fault` maps a parse failure to ValueError and a network
    fault to TransientProviderError. A flaky network must not inflate the
    schema-failure rate."""
    provider = FakeProvider(
        [_ok(), ValueError("could not parse"), TransientProviderError("timeout"), _ok()]
    )

    probe = probe_schema(provider, "fake-model", CASES[0], runs=4)

    assert probe.runs == 4
    assert probe.schema_failures == 1
    assert probe.transient_failures == 1
    assert probe.failure_rate == pytest.approx(0.25)


def test_probe_failure_rate_of_zero_runs_is_none():
    probe = SchemaProbe(
        provider="fake", model="m", runs=0, schema_failures=0, transient_failures=0
    )
    assert probe.failure_rate is None


# --- scorecard rows ----------------------------------------------------------


def test_run_cases_scores_each_case():
    provider = FakeProvider([_ok()])

    rows = run_cases(provider, "claude-opus-5", CASES, _judge())

    assert len(rows) == len(CASES)
    assert all(row.error is None for row in rows)
    assert rows[0].score.total == 18
    assert rows[0].cost == pytest.approx(1000 * 5 / 1e6 + 2000 * 25 / 1e6)


def test_run_cases_records_the_invented_pda_count():
    """`BaseProvider.generate` already runs the fidelity guard, so the hard
    grounding signal costs nothing extra and belongs on every row."""
    provider = FakeProvider([_ok(invented=["PDA inventado", "otro"])])

    rows = run_cases(provider, "claude-opus-5", CASES[:1], _judge())

    assert rows[0].invented == 2


def test_run_cases_records_a_failure_instead_of_aborting_the_sweep():
    provider = FakeProvider([ValueError("schema blew up"), _ok(), _ok()])

    rows = run_cases(provider, "claude-opus-5", CASES, _judge())

    assert len(rows) == len(CASES)
    assert "schema blew up" in rows[0].error
    assert rows[0].score is None
    assert all(row.error is None for row in rows[1:])


def test_run_cases_judges_against_the_field_specific_golden():
    """A Lenguajes plan judged against the Ética reference would be marked down
    for being on-topic, so the golden is selected per campo."""
    seen: list[str] = []
    judge = Judge(
        score=lambda golden, candidate, official: (
            seen.append(golden),
            JudgeScore(
                pda_fidelity=3,
                structural_completeness=3,
                coherence=3,
                spanish_register=3,
                rationale="",
            ),
        )[1]
    )

    run_cases(FakeProvider([_ok()]), "claude-opus-5", CASES, judge)

    assert len(set(seen)) == len({case.field_id for case in CASES})


def test_run_cases_shows_the_judge_what_the_teacher_sees():
    """The candidate text is the grounded render — ✓ / ⚠ markers included —
    not a bare dump, so the judge grades the delivered artifact."""
    seen: dict[str, str] = {}
    judge = Judge(
        score=lambda golden, candidate, official: (
            seen.update(candidate=candidate, official=official),
            JudgeScore(
                pda_fidelity=3,
                structural_completeness=3,
                coherence=3,
                spanish_register=3,
                rationale="",
            ),
        )[1]
    )

    run_cases(FakeProvider([_ok(invented=["PDA oficial"])]), "claude-opus-5", CASES[:1], judge)

    assert "FUERA DE TU SELECCIÓN" in seen["candidate"]
    assert "Fundamentación oficial" in seen["candidate"]
    assert seen["official"].strip()


# --- formatting --------------------------------------------------------------


def _row(**overrides) -> Row:
    base = dict(
        provider="claude",
        model="claude-opus-5",
        case_id=CASES[0].id,
        score=JudgeScore(
            pda_fidelity=5,
            structural_completeness=4,
            coherence=4,
            spanish_register=5,
            rationale="bien",
        ),
        usage=Usage(input_tokens=1000, output_tokens=2000),
        cost=0.055,
        invented=0,
        error=None,
    )
    return Row(**{**base, **overrides})


def test_scorecard_header_records_both_models():
    """Swapping the judge invalidates comparison against older scorecards, so
    the judge model is part of the committed record, not a runtime detail."""
    card = format_scorecard(
        rows=[_row()],
        probes=[],
        judge_model="claude-opus-5",
        generated_at="2026-07-28T12:00:00Z",
    )

    assert "claude-opus-5" in card
    assert "2026-07-28T12:00:00Z" in card
    assert "judge" in card.lower()


def test_scorecard_renders_a_failed_row_without_scores():
    card = format_scorecard(
        rows=[_row(score=None, usage=None, cost=None, invented=None, error="boom")],
        probes=[],
        judge_model="claude-opus-5",
        generated_at="2026-07-28T12:00:00Z",
    )

    assert "boom" in card


def test_scorecard_reports_the_schema_failure_rate():
    card = format_scorecard(
        rows=[_row()],
        probes=[
            SchemaProbe(
                provider="claude",
                model="claude-opus-5",
                runs=10,
                schema_failures=2,
                transient_failures=1,
            )
        ],
        judge_model="claude-opus-5",
        generated_at="2026-07-28T12:00:00Z",
    )

    assert "2/10" in card
    assert "20.0%" in card


def test_scorecard_omits_the_probe_section_when_it_was_not_run():
    card = format_scorecard(
        rows=[_row()], probes=[], judge_model="claude-opus-5", generated_at="now"
    )

    assert "schema" not in card.lower()


def test_scorecard_costs_are_absent_not_zero_for_self_hosted():
    """A self-hosted run has no per-token price. Printing $0.000 would read as
    'free and measured' when it is actually 'not billed this way'."""
    card = format_scorecard(
        rows=[_row(provider="vllm", model="Qwen3.6-40B", cost=None)],
        probes=[],
        judge_model="claude-opus-5",
        generated_at="now",
    )

    assert "n/a" in card
    assert "$0.000" not in card


def test_grounding_report_is_built_from_the_case_selection():
    """Sanity-check the seam `run_cases` relies on: a PDA outside the official
    selection is not marked official."""
    groups = [ContentPda(content="c", pdas=["PDA oficial"])]
    report = GroundingReport(selected=groups, invented=["PDA inventado"])

    assert report.is_official("PDA oficial")
    assert not report.is_official("PDA inventado")
