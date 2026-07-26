"""Adapter-level contract: raw SDK/instructor failures are translated onto the
port's two-way error contract before they ever reach the task layer.

`tasks.py` decides retry-vs-fail purely by exception type — `TransientProviderError`
retries, `_TERMINAL_ERRORS` fails the row. An adapter that lets a raw
`APITimeoutError` or `InstructorRetryException` escape matches neither clause, so
the task dies "unexpected" and its `LessonPlan` is orphaned at `status=generating`
forever. These tests pin the translation that prevents that.

Both adapters are constructed against fakes: no network call, no live model
discovery (`config.model` is always truthy, short-circuiting the
`config.model or raw_client.models.list()...` fallback).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import openai
import pytest
from instructor.core import InstructorRetryException
from pydantic import ValidationError

from lesson_plans.core.config import Config
from lesson_plans.core.ports.claude import ClaudeProvider
from lesson_plans.core.ports.llm import REQUEST_TIMEOUT_SECONDS, TransientProviderError
from lesson_plans.core.ports.openai_compat import OpenAICompatProvider
from lesson_plans.core.schema import Proyecto

CONFIG = Config(
    base_url="http://vllm.test/v1",
    model="test-model",
    api_key="dummy",
    anthropic_api_key="test-anthropic-key",
    anthropic_model="claude-test-model",
)


def _timeout_error() -> openai.APITimeoutError:
    return openai.APITimeoutError(
        request=httpx.Request("POST", "http://vllm.test/v1/chat/completions")
    )


def _retry_exception(cause: BaseException) -> InstructorRetryException:
    """The exact shape instructor raises: `raise InstructorRetryException(...) from cause`."""
    exc = InstructorRetryException("Request timed out.", n_attempts=1, total_usage=0)
    exc.__cause__ = cause
    return exc


def _schema_error() -> ValidationError:
    try:
        Proyecto.model_validate({})
    except ValidationError as exc:
        return exc
    raise AssertionError("Proyecto.model_validate({}) was expected to fail")


def _openai_provider(monkeypatch, error: BaseException | None) -> tuple[OpenAICompatProvider, dict]:
    """Build the vLLM adapter with a client whose completion call raises `error`."""
    recorded: dict = {}

    class _FakeOpenAI:
        def __init__(self, **kwargs):
            recorded.update(kwargs)

    def _fake_from_openai(client, mode=None):
        instructor_client = MagicMock()
        instructor_client.chat.completions.create_with_completion.side_effect = error
        return instructor_client

    monkeypatch.setattr("openai.OpenAI", _FakeOpenAI)
    monkeypatch.setattr("instructor.from_openai", _fake_from_openai)
    return OpenAICompatProvider.from_config(CONFIG), recorded


def _claude_provider(monkeypatch, error: BaseException | None) -> tuple[ClaudeProvider, dict]:
    recorded: dict = {}

    class _FakeAnthropic:
        def __init__(self, **kwargs):
            recorded.update(kwargs)

    def _fake_from_anthropic(client, **kwargs):
        instructor_client = MagicMock()
        instructor_client.messages.create_with_completion.side_effect = error
        return instructor_client

    monkeypatch.setattr("anthropic.Anthropic", _FakeAnthropic)
    monkeypatch.setattr("instructor.from_anthropic", _fake_from_anthropic)
    return ClaudeProvider.from_config(CONFIG), recorded


def test_vllm_client_is_built_with_an_explicit_timeout_and_no_sdk_retries(monkeypatch):
    """The HTTP layer must give up *before* Celery's soft time limit, so the failure
    arrives as a clean APITimeoutError instead of the task being decapitated mid-call.
    Retry policy belongs to the Celery task alone — never two nested retry loops."""
    _, recorded = _openai_provider(monkeypatch, error=None)

    assert recorded["timeout"] == REQUEST_TIMEOUT_SECONDS
    assert recorded["max_retries"] == 0


def test_vllm_timeout_becomes_a_transient_provider_error(monkeypatch):
    provider, _ = _openai_provider(monkeypatch, error=_timeout_error())

    with pytest.raises(TransientProviderError, match="timed out"):
        provider._complete("system", "user")


def test_vllm_timeout_wrapped_by_instructor_becomes_a_transient_provider_error(monkeypatch):
    """The real production shape: instructor re-raises with the SDK error as __cause__."""
    provider, _ = _openai_provider(monkeypatch, error=_retry_exception(_timeout_error()))

    with pytest.raises(TransientProviderError, match="timed out"):
        provider._complete("system", "user")


def test_vllm_connection_failure_becomes_a_transient_provider_error(monkeypatch):
    error = openai.APIConnectionError(
        request=httpx.Request("POST", "http://vllm.test/v1/chat/completions")
    )
    provider, _ = _openai_provider(monkeypatch, error=error)

    with pytest.raises(TransientProviderError):
        provider._complete("system", "user")


def test_vllm_schema_failure_stays_terminal_and_is_never_transient(monkeypatch):
    """A malformed Proyecto would fail identically on every retry. Translating it
    into TransientProviderError would burn the whole retry budget for nothing."""
    provider, _ = _openai_provider(monkeypatch, error=_schema_error())

    with pytest.raises(ValidationError):
        provider._complete("system", "user")


def test_vllm_schema_failure_wrapped_by_instructor_is_terminal_not_transient(monkeypatch):
    """instructor wraps parse failures in the same exception class as network failures.
    Only the cause distinguishes them; a ValueError is terminal to the task layer."""
    provider, _ = _openai_provider(monkeypatch, error=_retry_exception(_schema_error()))

    with pytest.raises(ValueError) as raised:
        provider._complete("system", "user")

    assert not isinstance(raised.value, TransientProviderError)


def test_claude_client_is_built_with_an_explicit_timeout_and_no_sdk_retries(monkeypatch):
    _, recorded = _claude_provider(monkeypatch, error=None)

    assert recorded["timeout"] == REQUEST_TIMEOUT_SECONDS
    assert recorded["max_retries"] == 0


def test_claude_timeout_becomes_a_transient_provider_error(monkeypatch):
    import anthropic

    error = anthropic.APITimeoutError(
        request=httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    )
    provider, _ = _claude_provider(monkeypatch, error=error)

    with pytest.raises(TransientProviderError):
        provider._complete("system", "user")


def test_claude_schema_failure_stays_terminal(monkeypatch):
    provider, _ = _claude_provider(monkeypatch, error=_schema_error())

    with pytest.raises(ValidationError):
        provider._complete("system", "user")
