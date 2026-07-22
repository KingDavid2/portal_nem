"""`generate` a single proyecto and render it for hand review.

    python -m lesson_plans.cli generate \
        --campo "Ética, Naturaleza y Sociedades" --grade SEGUNDO \
        --theme "La Independencia de México" --provider claude

Renders .md + .docx (mirroring the Planeabot example) under designs/export/.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from .config import Config
from .generation import GenerationRequest
from .pdas import pdas_for
from .ports.claude import ClaudeProvider
from .ports.llm import LLMProvider
from .ports.openai_compat import OpenAICompatProvider
from .render.docx import render_docx
from .render.markdown import render_md

_REPO_ROOT = Path(__file__).resolve().parents[2]
EXPORT_DIR = _REPO_ROOT / "designs" / "export"


def build_provider(name: str, config: Config) -> LLMProvider:
    if name == "claude":
        return ClaudeProvider.from_config(config)
    if name == "qwen":
        return OpenAICompatProvider.from_config(config)
    raise SystemExit(f"Unknown provider {name!r} (expected 'claude' or 'qwen').")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def generate(args: argparse.Namespace) -> None:
    config = Config.from_env()
    provider = build_provider(args.provider, config)
    result = provider.generate(
        GenerationRequest(campo=args.campo, grade=args.grade, theme=args.theme),
        pdas_for(args.campo),
    )

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"{args.provider}-{_slug(args.theme)}"
    docx_path = render_docx(result.proyecto, EXPORT_DIR / f"{stem}.docx")
    md_path = EXPORT_DIR / f"{stem}.md"
    md_path.write_text(render_md(result.proyecto), encoding="utf-8")

    print(f"Título: {result.proyecto.title}")
    print(f"Tokens: in={result.usage.input_tokens} out={result.usage.output_tokens}")
    if result.invented_pdas:
        print(f"⚠️  PDAs inventados ({len(result.invented_pdas)}):")
        for pda in result.invented_pdas:
            print(f"   - {pda}")
    else:
        print("PDA fidelity: OK (0 inventados)")
    print(f"Escrito: {docx_path}")
    print(f"Escrito: {md_path}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="lesson_plans")
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", help="Generate one proyecto and render it.")
    gen.add_argument("--campo", required=True)
    gen.add_argument("--grade", required=True)
    gen.add_argument("--theme", required=True)
    gen.add_argument("--provider", default="claude", choices=["claude", "qwen"])
    gen.set_defaults(func=generate)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
