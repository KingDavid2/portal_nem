"""OpenAICompatProvider — the self-hosted / affordable path (vLLM, Ollama, any
OpenAI-compatible endpoint), seeded by M0's client construction.

instructor runs in JSON mode: vLLM supports guided JSON decoding but not Anthropic
tool schemas. Whether the served model reliably fills the full nested Proyecto is part
of what Phase A measures — parse failures surface to the caller, they are not hidden.
"""

from __future__ import annotations

from ..config import Config
from ..schema import Proyecto
from .llm import BaseProvider, Usage

MAX_TOKENS = 20000
name = "qwen"


class OpenAICompatProvider(BaseProvider):
    # Labeled "qwen" for the scorecard — it is whatever the configured endpoint serves.
    name = "qwen"

    @classmethod
    def from_config(cls, config: Config) -> "OpenAICompatProvider":
        import instructor
        from openai import OpenAI

        raw_client = OpenAI(base_url=config.base_url, api_key=config.api_key)
        model = config.model or raw_client.models.list().data[0].id  # M0 discovery pattern
        client = instructor.from_openai(raw_client, mode=instructor.Mode.JSON)

        def complete(system: str, user: str) -> tuple[Proyecto, Usage]:
            proyecto, raw = client.chat.completions.create_with_completion(
                model=model,
                max_tokens=MAX_TOKENS,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_model=Proyecto,
            )
            usage = Usage(
                input_tokens=raw.usage.prompt_tokens,
                output_tokens=raw.usage.completion_tokens,
            )
            return proyecto, usage

        return cls(complete=complete, model=model)
