"""Thin wrapper over the OpenAI SDK: build, discover models, stream chat.

These functions are the raw transport M1 wraps: build_client + stream_chat
become the guts of OpenAICompatProvider; instructor layers schema-locked output
on top of the same client later.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, Iterator, Optional

from openai import OpenAI

from .config import Config


def build_client(config: Config) -> OpenAI:
    return OpenAI(base_url=config.base_url, api_key=config.api_key)


def list_models(client: OpenAI) -> list[str]:
    return [m.id for m in client.models.list().data]


def resolve_model(client: OpenAI, model: Optional[str]) -> str:
    """Explicit config wins; otherwise default to the first served model."""
    if model:
        return model
    served = list_models(client)
    if not served:
        raise RuntimeError("No model configured and the endpoint serves none.")
    return served[0]


def stream_chat(
    client: OpenAI,
    model: str,
    messages: Iterable[dict[str, str]],
    on_usage: Optional[Callable[[Any], None]] = None,
) -> Iterator[str]:
    """Yield token text as it streams. Empty deltas are skipped.

    The final usage chunk (when the endpoint returns one) is handed to on_usage
    rather than yielded, so callers get clean token text.
    """
    stream = client.chat.completions.create(
        model=model,
        messages=list(messages),
        stream=True,
        stream_options={"include_usage": True},
    )
    for chunk in stream:
        usage = getattr(chunk, "usage", None)
        if usage is not None and on_usage is not None:
            on_usage(usage)
        if not chunk.choices:
            continue
        content = chunk.choices[0].delta.content
        if content:
            yield content
