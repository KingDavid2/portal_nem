"""Scorecard runner: Claude vs self-hosted Qwen on the eval cases.

For each case x provider: generate, render, judge against the golden, and record
scores, tokens, cost, and invented-PDA count. Qwen schema-fill failures are surfaced
as errors in the table, not hidden — whether the self-hosted model can reliably fill
the nested schema is part of what Phase A measures.

    python -m lesson_plans.eval.run
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..config import Config
from ..pdas import pdas_for
from ..ports.claude import ClaudeProvider
from ..ports.llm import LLMProvider, Usage
from ..ports.openai_compat import OpenAICompatProvider
from ..render.markdown import render_md
from .cases import CASES
from .golden import golden_text
from .judge import Judge, JudgeScore

# Per-1M-token cost (input, output). Claude API rates; Qwen is self-hosted (~electricity).
COST_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-opus-4-8": (5.0, 25.0),
    "claude-opus-4-7": (5.0, 25.0),
    "claude-sonnet-5": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
}


def usd(usage: Usage, model: str) -> Optional[float]:
    rate = COST_PER_MTOK.get(model)
    if rate is None:
        return None  # self-hosted / unknown -> not billed per token
    return usage.input_tokens * rate[0] / 1e6 + usage.output_tokens * rate[1] / 1e6


@dataclass
class Row:
    provider: str
    theme: str
    score: Optional[JudgeScore]
    usage: Optional[Usage]
    cost: Optional[float]
    invented: Optional[int]
    error: Optional[str]


def run() -> list[Row]:
    config = Config.from_env()
    judge = Judge.from_config(config)
    golden = golden_text()

    providers: list[tuple[LLMProvider, str]] = [
        (ClaudeProvider.from_config(config), config.anthropic_model),
        (OpenAICompatProvider.from_config(config), config.model or "self-hosted"),
    ]

    rows: list[Row] = []
    for provider, model in providers:
        for case in CASES:
            try:
                result = provider.generate(case, pdas_for(case.campo))
                score = judge.evaluate(golden, render_md(result.proyecto))
                rows.append(
                    Row(
                        provider=provider.name,
                        theme=case.theme,
                        score=score,
                        usage=result.usage,
                        cost=usd(result.usage, model),
                        invented=len(result.invented_pdas),
                        error=None,
                    )
                )
            except Exception as exc:  # schema-fill failure, transport error, etc.
                rows.append(
                    Row(provider.name, case.theme, None, None, None, None, error=str(exc)[:120])
                )
    return rows


def _fmt(rows: list[Row]) -> str:
    header = f"{'provider':8} {'PDAfid':6} {'struct':6} {'coher':6} {'reg':4} {'total':5} {'inv':3} {'tok(in/out)':13} {'cost':7} theme"
    lines = [header, "-" * len(header)]
    for r in rows:
        if r.error:
            lines.append(f"{r.provider:8} ERROR: {r.error}  ({r.theme})")
            continue
        s, u = r.score, r.usage
        cost = "n/a" if r.cost is None else f"${r.cost:.3f}"
        lines.append(
            f"{r.provider:8} "
            f"{s.pda_fidelity:^6} {s.structural_completeness:^6} {s.coherence:^6} "
            f"{s.spanish_register:^4} {s.total:^5} {r.invented:^3} "
            f"{u.input_tokens}/{u.output_tokens:<7} {cost:7} {r.theme}"
        )
    return "\n".join(lines)


def main() -> None:
    rows = run()
    print(_fmt(rows))


if __name__ == "__main__":
    main()
