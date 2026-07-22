"""EmbeddingProvider contract — the live endpoint is exercised at integration time; the
injected embed callable pins the adapter's pass-through here."""

from __future__ import annotations

from lesson_plans.ports.embeddings import OpenAICompatEmbedder


def test_embedder_passes_texts_through_and_returns_vectors():
    calls: list[list[str]] = []

    def fake_embed(texts: list[str]) -> list[list[float]]:
        calls.append(texts)
        return [[float(len(t))] for t in texts]

    embedder = OpenAICompatEmbedder(embed=fake_embed, model="e5")
    vectors = embedder.embed(["ab", "abcd"])

    assert vectors == [[2.0], [4.0]]
    assert calls == [["ab", "abcd"]]
    assert embedder.name == "qwen-embed"
    assert embedder.model == "e5"
