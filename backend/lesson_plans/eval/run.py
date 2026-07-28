"""Scorecard assembly: generate, render, judge, and cost each case.

Providers are constructed by the caller and injected, deliberately *not* taken
from `core.factory.build_provider()` — that reads one global `LLM_PROVIDER`
setting, but a scorecard needs several providers live in the same process.

Every failure lands in the table rather than aborting the sweep: a provider that
cannot fill the nested `Proyecto` schema is a result, not an accident, and it is
half of what P2 exists to measure.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..core.catalog_pdas import content_pdas_for
from ..core.grounding import GroundingReport
from ..core.ports.llm import LLMProvider, TransientProviderError, Usage
from ..core.render.markdown import render_md
from .cases import EvalCase
from .golden import golden_text
from .judge import Judge, JudgeScore

# Per-1M-token cost (input, output), Anthropic first-party rates. Self-hosted
# models are absent on purpose — they are not billed per token, and inventing a
# figure for them would make the cost column silently incomparable.
COST_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-fable-5": (10.0, 50.0),
    "claude-opus-5": (5.0, 25.0),
    "claude-opus-4-8": (5.0, 25.0),
    "claude-opus-4-7": (5.0, 25.0),
    "claude-sonnet-5": (3.0, 15.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
}


def usd(usage: Usage, model: str) -> Optional[float]:
    """Dollar cost of one generation, or `None` when the model is not billed per token."""
    rate = COST_PER_MTOK.get(model)
    if rate is None:
        return None
    return usage.input_tokens * rate[0] / 1e6 + usage.output_tokens * rate[1] / 1e6


@dataclass(frozen=True)
class Row:
    provider: str
    model: str
    case_id: str
    score: Optional[JudgeScore]
    usage: Optional[Usage]
    cost: Optional[float]
    invented: Optional[int]
    error: Optional[str]


@dataclass(frozen=True)
class SchemaProbe:
    """How often a provider fails to fill the nested `Proyecto` schema."""

    provider: str
    model: str
    runs: int
    schema_failures: int
    transient_failures: int

    @property
    def failure_rate(self) -> Optional[float]:
        if not self.runs:
            return None
        return self.schema_failures / self.runs


def official_text(case: EvalCase) -> str:
    """The teacher's selection, verbatim — the judge's fidelity source."""
    groups = content_pdas_for(case.field_id, case.selection_list)
    lines: list[str] = []
    for group in groups:
        lines.append(f"Contenido: {group.content}")
        lines += [f"  - PDA: {pda}" for pda in group.pdas]
    return "\n".join(lines)


def run_cases(
    provider: LLMProvider,
    model: str,
    cases: tuple[EvalCase, ...] | list[EvalCase],
    judge: Judge,
) -> list[Row]:
    """Generate and score every case, recording failures as rows."""
    rows: list[Row] = []
    for case in cases:
        groups = content_pdas_for(case.field_id, case.selection_list)
        try:
            result = provider.generate(case.request, groups)
        except Exception as exc:  # schema failure, transport fault, anything
            rows.append(
                Row(
                    provider=provider.name,
                    model=model,
                    case_id=case.id,
                    score=None,
                    usage=None,
                    cost=None,
                    invented=None,
                    error=f"{type(exc).__name__}: {exc}"[:160],
                )
            )
            continue

        # The judge grades the artifact the teacher actually receives, markers
        # and official-basis section included.
        grounding = GroundingReport(selected=groups, invented=result.invented_pdas)
        candidate = render_md(result.proyecto, grounding)
        score = judge.evaluate(
            golden=golden_text(case.field_id),
            candidate=candidate,
            official=official_text(case),
        )
        rows.append(
            Row(
                provider=provider.name,
                model=model,
                case_id=case.id,
                score=score,
                usage=result.usage,
                cost=usd(result.usage, model),
                invented=len(result.invented_pdas),
                error=None,
            )
        )
    return rows


def probe_schema(
    provider: LLMProvider, model: str, case: EvalCase, runs: int
) -> SchemaProbe:
    """Generate `case` N times and count terminal schema-parse failures.

    Only `ValueError` counts: `raise_provider_fault` maps a parse failure to it
    and a retryable network fault to `TransientProviderError`. Folding the two
    together would let a flaky link masquerade as an unreliable schema filler.
    """
    groups = content_pdas_for(case.field_id, case.selection_list)
    schema_failures = 0
    transient_failures = 0
    for _ in range(runs):
        try:
            provider.generate(case.request, groups)
        except ValueError:
            schema_failures += 1
        except TransientProviderError:
            transient_failures += 1
    return SchemaProbe(
        provider=provider.name,
        model=model,
        runs=runs,
        schema_failures=schema_failures,
        transient_failures=transient_failures,
    )


_HEADER = (
    f"{'provider':9} {'PDAfid':6} {'struct':6} {'coher':6} {'reg':4} "
    f"{'total':5} {'inv':3} {'tok(in/out)':13} {'cost':8} case"
)


def format_scorecard(
    rows: list[Row],
    probes: list[SchemaProbe],
    judge_model: str,
    generated_at: str,
) -> str:
    """A committed Markdown scorecard; a later run diffs against it."""
    models = sorted({row.model for row in rows})
    out = [
        "# Eval scorecard",
        "",
        f"- Generated: {generated_at}",
        f"- Generation model(s): {', '.join(models) or 'n/a'}",
        f"- Judge model: {judge_model}",
        "",
        "> Same-family bias: a Claude-judged Claude generation scores itself. The",
        "> judge model is pinned here so a future run can swap it and compare.",
        "",
        "```",
        _HEADER,
        "-" * len(_HEADER),
    ]
    for row in rows:
        if row.error:
            out.append(f"{row.provider:9} ERROR: {row.error}  ({row.case_id})")
            continue
        score, usage = row.score, row.usage
        cost = "n/a" if row.cost is None else f"${row.cost:.3f}"
        tokens = f"{usage.input_tokens}/{usage.output_tokens}"
        out.append(
            f"{row.provider:9} "
            f"{score.pda_fidelity:^6} {score.structural_completeness:^6} "
            f"{score.coherence:^6} {score.spanish_register:^4} {score.total:^5} "
            f"{row.invented:^3} {tokens:13} {cost:8} {row.case_id}"
        )
    out.append("```")

    if probes:
        out += ["", "## Schema-failure rate", ""]
        for probe in probes:
            rate = probe.failure_rate
            pct = "n/a" if rate is None else f"{rate * 100:.1f}%"
            out.append(
                f"- `{probe.provider}` / `{probe.model}`: "
                f"{probe.schema_failures}/{probe.runs} terminal parse failures ({pct}); "
                f"{probe.transient_failures} transient fault(s), not counted."
            )

    scored = [row.score for row in rows if row.score is not None]
    if scored:
        from .judge import average_scores

        out += ["", "## Averages", ""]
        for axis, value in average_scores(scored).items():
            out.append(f"- {axis}: {value:.2f}")

    return "\n".join(out) + "\n"
