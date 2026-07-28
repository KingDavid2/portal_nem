"""Provider factory selects an adapter from Django settings only (design
Decision: Provider factory reading `LLM_PROVIDER`; Scenarios: Default
configuration selects vLLM; Switching to Claude requires only configuration).

`LLM_MODEL` / `ANTHROPIC_MODEL` are set explicitly so adapter construction
never triggers a live model-discovery network call (config.model is truthy,
short-circuiting the `config.model or raw_client.models.list()...` fallback
in `ports/openai_compat.py`).

`LLM_PROVIDER` is pinned rather than left to the settings default. Settings are
built from the developer's real `.env`, so a machine configured for Claude made
the vLLM cases assert against `LLM_PROVIDER=claude` and fail. What the factory
owns is the id -> adapter mapping; which id is configured is not its behaviour.
"""

from __future__ import annotations

from lesson_plans.core.factory import build_provider
from lesson_plans.core.ports.claude import ClaudeProvider
from lesson_plans.core.ports.openai_compat import OpenAICompatProvider


def test_default_configuration_selects_the_openai_compat_vllm_adapter(settings):
    settings.LLM_PROVIDER = "vllm"
    settings.LLM_MODEL = "test-model"

    provider = build_provider()

    assert isinstance(provider, OpenAICompatProvider)
    assert provider.name == "qwen"
    assert provider.model == "test-model"


def test_llm_provider_claude_selects_the_claude_adapter(settings):
    settings.LLM_PROVIDER = "claude"
    settings.ANTHROPIC_API_KEY = "test-anthropic-key"
    settings.ANTHROPIC_MODEL = "claude-test-model"

    provider = build_provider()

    assert isinstance(provider, ClaudeProvider)
    assert provider.name == "claude"
    assert provider.model == "claude-test-model"


def test_switching_provider_requires_only_the_env_setting(settings):
    """No service/task-layer code changes needed to swap providers — only
    `LLM_PROVIDER` changes between the two calls below."""
    settings.LLM_PROVIDER = "vllm"
    settings.LLM_MODEL = "test-model"
    default_provider = build_provider()

    settings.LLM_PROVIDER = "claude"
    settings.ANTHROPIC_API_KEY = "test-anthropic-key"
    claude_provider = build_provider()

    assert default_provider.name != claude_provider.name
    assert isinstance(default_provider, OpenAICompatProvider)
    assert isinstance(claude_provider, ClaudeProvider)
