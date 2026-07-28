"""`manage.py run_evals` — the on-demand generation-quality gate (Quizzy P2).

Deliberately a management command and not a pytest test: a full sweep spends
real tokens and real minutes, so it is something you invoke before a prompt or
model change ships, not something CI runs per commit. The token-free parts are
covered by `lesson_plans/eval/test_*.py`, which the normal suite does collect.

    python manage.py run_evals --provider claude
    python manage.py run_evals --provider claude --schema-runs 10
    python manage.py run_evals --provider claude --provider vllm --out card.md

Providers are built here rather than through `core.factory.build_provider()`:
the factory reads one global `LLM_PROVIDER`, but a scorecard needs more than one
provider live in the same process.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from lesson_plans.core.config import Config
from lesson_plans.core.ports.claude import ClaudeProvider
from lesson_plans.core.ports.llm import LLMProvider
from lesson_plans.core.ports.openai_compat import OpenAICompatProvider
from lesson_plans.eval.cases import CASES, case_by_id
from lesson_plans.eval.judge import Judge
from lesson_plans.eval.run import (
    Row,
    SchemaProbe,
    format_scorecard,
    probe_schema,
    run_cases,
)

SCORECARD_DIR = Path(__file__).resolve().parents[2] / "eval" / "scorecards"


def _config() -> Config:
    return Config(
        base_url=settings.LLM_BASE_URL,
        model=settings.LLM_MODEL,
        api_key=settings.LLM_API_KEY,
        anthropic_api_key=settings.ANTHROPIC_API_KEY,
        anthropic_model=settings.ANTHROPIC_MODEL,
    )


def _build(provider_id: str, config: Config) -> tuple[LLMProvider, str]:
    """Return the adapter and the model id it will actually call.

    The model is returned alongside because the scorecard prices and labels the
    run by it, and for the self-hosted path it may be resolved by discovery
    rather than configured.
    """
    if provider_id == "claude":
        if not config.anthropic_api_key:
            raise CommandError(
                "ANTHROPIC_API_KEY is not set. Export it or add it to .env "
                "before running the Claude arm."
            )
        provider = ClaudeProvider.from_config(config)
    else:
        provider = OpenAICompatProvider.from_config(config)
    return provider, provider.model


class Command(BaseCommand):
    help = "Generate, judge, and score planeaciones; write a committable scorecard."

    def add_arguments(self, parser):
        parser.add_argument(
            "--provider",
            action="append",
            dest="providers",
            choices=["claude", "vllm"],
            help="Provider arm to run; repeat for several. Default: claude.",
        )
        parser.add_argument(
            "--case",
            action="append",
            dest="case_ids",
            help="Eval case id to run; repeat for several. Default: all.",
        )
        parser.add_argument(
            "--schema-runs",
            type=int,
            default=0,
            help=(
                "Generate one case N extra times per provider to measure the "
                "terminal schema-parse failure rate. Default: 0 (skip)."
            ),
        )
        parser.add_argument(
            "--out",
            help="Where to write the scorecard. Default: eval/scorecards/<timestamp>.md",
        )

    def handle(self, *args, **options):
        providers = options["providers"] or ["claude"]
        cases = self._cases(options["case_ids"])
        schema_runs = options["schema_runs"]
        if schema_runs < 0:
            raise CommandError("--schema-runs cannot be negative.")

        config = _config()
        judge = Judge.from_settings()

        rows: list[Row] = []
        probes: list[SchemaProbe] = []
        for provider_id in providers:
            provider, model = _build(provider_id, config)
            self.stdout.write(f"→ {provider.name} ({model}): {len(cases)} case(s)")
            rows += run_cases(provider, model, cases, judge)

            if schema_runs:
                self.stdout.write(f"  schema probe: {schema_runs} run(s)")
                probes.append(probe_schema(provider, model, cases[0], schema_runs))

        card = format_scorecard(
            rows=rows,
            probes=probes,
            judge_model=settings.EVAL_JUDGE_MODEL,
            generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )

        path = self._out_path(options["out"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(card, encoding="utf-8")

        self.stdout.write(card)
        failed = sum(1 for row in rows if row.error)
        if failed:
            self.stdout.write(self.style.WARNING(f"{failed} case(s) failed — see above."))
        self.stdout.write(self.style.SUCCESS(f"Scorecard written to {path}"))

    def _cases(self, case_ids):
        if not case_ids:
            return list(CASES)
        try:
            return [case_by_id(case_id) for case_id in case_ids]
        except KeyError as exc:
            raise CommandError(str(exc)) from exc

    def _out_path(self, out) -> Path:
        if out:
            return Path(out)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return SCORECARD_DIR / f"{stamp}.md"
