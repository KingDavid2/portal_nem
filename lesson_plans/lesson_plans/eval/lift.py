"""Phase B lift: no-RAG baseline vs RAG retrieval on the same cases (roadmap task 9).

Two arms per case, same provider:
  - baseline: the model gets NO contenidos/PDAs and must supply its own -> expect
    invented PDAs (absent from the corpus) and weaker fidelity.
  - rag: retrieve real contenidos/PDAs from the corpus by theme -> expect zero invented.

Both arms count invented PDAs against the WHOLE corpus (not just what was fed), so the
comparison is apples-to-apples. The delta is the measured value of retrieval.

    python -m lesson_plans.eval.lift            # self-hosted qwen, default
    python -m lesson_plans.eval.lift --provider claude
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Optional

from ..config import Config
from ..corpus import Corpus
from ..ports.embeddings import OpenAICompatEmbedder
from ..ports.llm import LLMProvider, find_invented_pdas
from ..render.markdown import render_md
from .cases import CASES
from .golden import golden_text
from .judge import Judge, JudgeScore

RETRIEVE_K = 1


@dataclass
class ArmResult:
    arm: str
    theme: str
    invented: Optional[int]
    total_pdas: Optional[int]
    score: Optional[JudgeScore]
    error: Optional[str]


def _build_provider(name: str, config: Config) -> LLMProvider:
    if name == "claude":
        from ..ports.claude import ClaudeProvider

        return ClaudeProvider.from_config(config)
    from ..ports.openai_compat import OpenAICompatProvider

    return OpenAICompatProvider.from_config(config)


def run(provider_name: str = "qwen") -> list[ArmResult]:
    config = Config.from_env()
    provider = _build_provider(provider_name, config)
    corpus = Corpus.build(OpenAICompatEmbedder.from_config(config))
    judge = Judge.from_config(config)
    golden = golden_text()
    allowed = corpus.all_content_pdas()

    results: list[ArmResult] = []
    for case in CASES:
        for arm in ("baseline", "rag"):
            pdas = [] if arm == "baseline" else corpus.retrieve(case.theme, k=RETRIEVE_K)
            try:
                result = provider.generate(case, pdas)
                invented = find_invented_pdas(result.proyecto, allowed)
                results.append(
                    ArmResult(
                        arm=arm,
                        theme=case.theme,
                        invented=len(invented),
                        total_pdas=len(result.proyecto.all_pdas()),
                        score=judge.evaluate(golden, render_md(result.proyecto)),
                        error=None,
                    )
                )
            except Exception as exc:  # schema-fill / transport failure — surfaced, not hidden
                results.append(ArmResult(arm, case.theme, None, None, None, error=str(exc)[:120]))
    return results


def _fmt(results: list[ArmResult]) -> str:
    header = f"{'arm':9} {'inv/total':10} {'PDAfid':6} {'total':5} theme"
    lines = [header, "-" * len(header)]
    for r in results:
        if r.error:
            lines.append(f"{r.arm:9} ERROR: {r.error}  ({r.theme})")
            continue
        s = r.score
        lines.append(
            f"{r.arm:9} {f'{r.invented}/{r.total_pdas}':10} "
            f"{s.pda_fidelity:^6} {s.total:^5} {r.theme}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="lesson_plans.eval.lift")
    parser.add_argument("--provider", default="qwen", choices=["claude", "qwen"])
    args = parser.parse_args(argv)
    print(_fmt(run(args.provider)))


if __name__ == "__main__":
    main()
