"""EmbeddingProvider port + the self-hosted OpenAI-compat adapter (Phase B RAG).

Mirrors the LLMProvider seam: one `embed(texts) -> vectors` callable injected into a
thin adapter, so the live client is exercised at integration time while unit tests pin
the contract with a fake. The self-hosted Qwen3-Embedding-4B endpoint (a second vLLM
process on :8001) speaks the OpenAI wire protocol, so pointing at a different embedder —
or dropping in a local sentence-transformers adapter for offline use — is a config swap,
not a code change.
"""

from __future__ import annotations

from typing import Callable, Protocol

from ..config import Config

# embed(texts) -> one vector per input text
EmbedFn = Callable[[list[str]], "list[list[float]]"]


class EmbeddingProvider(Protocol):
    name: str

    def embed(self, texts: list[str]) -> list[list[float]]:
        ...


class OpenAICompatEmbedder:
    """Embeds via any OpenAI-compatible `/v1/embeddings` endpoint (vLLM, Ollama, ...)."""

    name = "qwen-embed"

    def __init__(self, embed: EmbedFn, model: str) -> None:
        self._embed = embed
        self.model = model

    @classmethod
    def from_config(cls, config: Config) -> "OpenAICompatEmbedder":
        from openai import OpenAI

        client = OpenAI(base_url=config.embed_base_url, api_key=config.api_key)
        model = config.embed_model or client.models.list().data[0].id  # M0 discovery pattern

        def embed(texts: list[str]) -> list[list[float]]:
            response = client.embeddings.create(model=model, input=texts)
            # vLLM preserves input order in `data`; sort by index to be safe.
            return [item.embedding for item in sorted(response.data, key=lambda d: d.index)]

        return cls(embed=embed, model=model)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts)
