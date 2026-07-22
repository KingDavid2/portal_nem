"""ClaudeProvider — the quality ceiling (Anthropic SDK + instructor tool-calling).

If even this can't produce an acceptable planeación, the product is dead. instructor
enforces the Proyecto schema via Anthropic tool use; usage comes from the raw response.
"""

from __future__ import annotations

from ..config import Config
from ..schema import Proyecto
from .llm import BaseProvider, Complete, Usage

MAX_TOKENS = 16000


class ClaudeProvider(BaseProvider):
    name = "claude"

    @classmethod
    def from_config(cls, config: Config) -> "ClaudeProvider":
        import instructor
        from anthropic import Anthropic

        client = instructor.from_anthropic(Anthropic(api_key=config.anthropic_api_key))
        model = config.anthropic_model

        def complete(system: str, user: str) -> tuple[Proyecto, Usage]:
            proyecto, raw = client.messages.create_with_completion(
                model=model,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=[{"role": "user", "content": user}],
                response_model=Proyecto,
            )
            usage = Usage(
                input_tokens=raw.usage.input_tokens,
                output_tokens=raw.usage.output_tokens,
            )
            return proyecto, usage

        return cls(complete=complete, model=model)
