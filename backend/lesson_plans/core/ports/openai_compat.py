"""OpenAICompatProvider — the self-hosted / affordable path (vLLM, Ollama, any
OpenAI-compatible endpoint), seeded by M0's client construction.

instructor runs in JSON mode: vLLM supports guided JSON decoding but not Anthropic
tool schemas. Whether the served model reliably fills the full nested Proyecto is part
of what Phase A measures — parse failures surface to the caller, they are not hidden.
"""

from __future__ import annotations

from ..config import Config
from ..schema import Proyecto
from .llm import REQUEST_TIMEOUT_SECONDS, BaseProvider, Usage, raise_provider_fault

MAX_TOKENS = 20000
name = "qwen"


class OpenAICompatProvider(BaseProvider):
    # Labeled "qwen" for the scorecard — it is whatever the configured endpoint serves.
    name = "qwen"

    @classmethod
    def from_config(cls, config: Config) -> "OpenAICompatProvider":
        import instructor
        import openai
        from openai import OpenAI

        # Retryable: the endpoint is reachable-but-unwell, so the same request may
        # well succeed later. APITimeoutError subclasses APIConnectionError; it is
        # listed anyway because it is the failure this codebase actually sees.
        transient = (
            openai.APITimeoutError,
            openai.APIConnectionError,
            openai.RateLimitError,
            openai.InternalServerError,
        )

        # max_retries=0: retry policy belongs to the Celery task, which owns the
        # backoff and the row's status. Two nested retry loops would multiply the
        # wall-clock budget without either layer knowing about the other.
        raw_client = OpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout=REQUEST_TIMEOUT_SECONDS,
            max_retries=0,
        )
        model = config.model or raw_client.models.list().data[0].id  # M0 discovery pattern
        client = instructor.from_openai(raw_client, mode=instructor.Mode.JSON)

        def complete(system: str, user: str) -> tuple[Proyecto, Usage]:
            try:
                proyecto, raw = client.chat.completions.create_with_completion(
                    model=model,
                    max_tokens=MAX_TOKENS,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    response_model=Proyecto,
                )
            except Exception as exc:
                raise_provider_fault(exc, transient)
            usage = Usage(
                input_tokens=raw.usage.prompt_tokens,
                output_tokens=raw.usage.completion_tokens,
            )
            return proyecto, usage

        return cls(complete=complete, model=model)
