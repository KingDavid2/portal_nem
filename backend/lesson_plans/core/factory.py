"""Provider factory: selects the `LLMProvider` adapter from Django settings.

Reads `LLM_PROVIDER` (default: the OpenAI-compatible/vLLM path) and builds the
M1 `Config` dataclass from settings, then constructs the matching adapter. The
service/task layer calls only `build_provider()` — the hexagonal port boundary
(`ports/llm.py::LLMProvider`) never changes when the provider is swapped
(design Decision: Provider factory reading `LLM_PROVIDER`).
"""

from __future__ import annotations

from django.conf import settings

from .config import Config
from .ports.claude import ClaudeProvider
from .ports.llm import LLMProvider
from .ports.openai_compat import OpenAICompatProvider


def _build_config() -> Config:
    return Config(
        base_url=settings.LLM_BASE_URL,
        model=settings.LLM_MODEL,
        api_key=settings.LLM_API_KEY,
        anthropic_api_key=settings.ANTHROPIC_API_KEY,
        anthropic_model=settings.ANTHROPIC_MODEL,
    )


def build_provider() -> LLMProvider:
    """Return the configured `LLMProvider`. Default (`LLM_PROVIDER` unset or
    anything other than `"claude"`) selects `OpenAICompatProvider` (vLLM)."""
    config = _build_config()
    if settings.LLM_PROVIDER == "claude":
        return ClaudeProvider.from_config(config)
    return OpenAICompatProvider.from_config(config)
