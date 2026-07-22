"""The LLMProvider port + shared generate() orchestration and the PDA-fidelity guard.

Both adapters (Claude ceiling, OpenAI-compat self-hosted) reduce to one seam: a
`complete(system, user) -> (Proyecto, Usage)` structured-completion callable. generate()
wraps that with the deterministic hallucination guard — every output PDA must appear in
the input fixture. In Phase B the same guard runs against the retrieved corpus.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Protocol

from ..generation import GenerationRequest, build_messages
from ..schema import ContentPda, Proyecto

# complete(system, user) -> (proyecto, usage)
Complete = Callable[[str, str], "tuple[Proyecto, Usage]"]


@dataclass(frozen=True)
class Usage:
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class GenerationResult:
    proyecto: Proyecto
    usage: Usage
    invented_pdas: list[str]


def _norm(text: str) -> str:
    """Collapse whitespace + casefold so trivial reformatting is not flagged as invention."""
    return re.sub(r"\s+", " ", text).strip().casefold()


def find_invented_pdas(proyecto: Proyecto, allowed: list[ContentPda]) -> list[str]:
    """Output PDAs (verbatim) absent from the allowed fixture — the hallucination signal."""
    allowed_norms = {_norm(pda) for group in allowed for pda in group.pdas}
    return [pda for pda in proyecto.all_pdas() if _norm(pda) not in allowed_norms]


class LLMProvider(Protocol):
    name: str

    def generate(self, request: GenerationRequest, pdas: list[ContentPda]) -> GenerationResult:
        ...


class BaseProvider:
    """Shared orchestration; adapters supply `name`, `complete`, and a `from_config`."""

    name: str = "base"

    def __init__(self, complete: Complete, model: str) -> None:
        self._complete = complete
        self.model = model

    def generate(self, request: GenerationRequest, pdas: list[ContentPda]) -> GenerationResult:
        messages = build_messages(request, pdas)
        system, user = messages[0]["content"], messages[1]["content"]
        proyecto, usage = self._complete(system, user)
        return GenerationResult(
            proyecto=proyecto,
            usage=usage,
            invented_pdas=find_invented_pdas(proyecto, pdas),
        )
