"""The LLMProvider port + shared generate() orchestration and the PDA-fidelity guard.

Both adapters (Claude ceiling, OpenAI-compat self-hosted) reduce to one seam: a
`complete(system, user) -> (Proyecto, Usage)` structured-completion callable. generate()
wraps that with the deterministic hallucination guard — every output PDA must appear in
the input fixture. In Phase B the same guard runs against the retrieved corpus.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, NoReturn, Protocol

from ..generation import GenerationRequest, build_messages
from ..grounding import find_invented_pdas
from ..schema import ContentPda, Proyecto

# complete(system, user) -> (proyecto, usage)
Complete = Callable[[str, str], "tuple[Proyecto, Usage]"]

# How long a single structured-completion HTTP call may take. Deliberately below
# the Celery task's soft time limit so the HTTP layer always gives up first and
# raises a clean, translatable timeout — rather than the task being decapitated
# mid-call by Celery, which leaves nothing to translate.
REQUEST_TIMEOUT_SECONDS = 540


class TransientProviderError(Exception):
    """Raised by a provider adapter for a retryable network/provider failure
    (timeout, connection, 5xx, rate limit) — never for a schema/parse failure.

    Lives here, on the port, because both adapters must raise it and neither may
    import the Django task layer.
    """


def raise_provider_fault(exc: Exception, transient: tuple[type[BaseException], ...]) -> NoReturn:
    """Re-raise `exc` as the port's error contract sees it.

    The task layer routes purely on exception type, so every failure leaving an
    adapter must be one of: `TransientProviderError` (retry), a terminal error the
    task already knows (`ValidationError` / `KeyError` / `ValueError` — fail the
    row), or an unrelated exception passed through untouched.

    instructor raises the *same* exception class for a network timeout and for a
    schema-parse failure; only `__cause__` tells them apart. Getting this wrong in
    either direction is costly: a parse failure classified as transient burns the
    whole retry budget re-producing identical garbage, and a timeout classified as
    terminal fails a plan that a retry would have completed.
    """
    from instructor.core import InstructorError

    if isinstance(exc, transient) or isinstance(exc.__cause__, transient):
        raise TransientProviderError(str(exc) or type(exc).__name__) from exc
    if isinstance(exc, InstructorError):
        # Not a transient cause, so this is a structured-output failure. ValueError
        # is terminal to the task layer; instructor's own class is not.
        raise ValueError(str(exc) or type(exc).__name__) from exc
    raise exc


@dataclass(frozen=True)
class Usage:
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class GenerationResult:
    proyecto: Proyecto
    usage: Usage
    invented_pdas: list[str]


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
