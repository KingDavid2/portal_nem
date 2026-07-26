"""ClaudeProvider — the quality ceiling (Anthropic SDK + instructor tool-calling).

If even this can't produce an acceptable planeación, the product is dead. instructor
enforces the Proyecto schema via Anthropic tool use; usage comes from the raw response.
"""

from __future__ import annotations

from ..config import Config
from ..schema import Proyecto
from .llm import REQUEST_TIMEOUT_SECONDS, BaseProvider, Complete, Usage, raise_provider_fault

MAX_TOKENS = 16000


class ClaudeProvider(BaseProvider):
    name = "claude"

    @classmethod
    def from_config(cls, config: Config) -> "ClaudeProvider":
        import anthropic
        import instructor
        from anthropic import Anthropic

        # Same contract as the vLLM adapter: the task layer routes on exception
        # type, so both adapters must speak it. See `ports/llm.py`.
        transient = (
            anthropic.APITimeoutError,
            anthropic.APIConnectionError,
            anthropic.RateLimitError,
            anthropic.InternalServerError,
        )

        client = instructor.from_anthropic(
            Anthropic(
                api_key=config.anthropic_api_key,
                timeout=REQUEST_TIMEOUT_SECONDS,
                max_retries=0,
            )
        )
        model = config.anthropic_model

        def complete(system: str, user: str) -> tuple[Proyecto, Usage]:
            try:
                proyecto, raw = client.messages.create_with_completion(
                    model=model,
                    max_tokens=MAX_TOKENS,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                    response_model=Proyecto,
                )
            except Exception as exc:
                raise_provider_fault(exc, transient)
            usage = Usage(
                input_tokens=raw.usage.input_tokens,
                output_tokens=raw.usage.output_tokens,
            )
            return proyecto, usage

        return cls(complete=complete, model=model)
