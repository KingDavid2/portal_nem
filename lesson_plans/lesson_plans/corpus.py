"""Fase 6 corpus + retrieval — the Phase B RAG replacement for the pdas.py stand-in.

Contenidos/PDAs live in `data/fase6_corpus.json`, get embedded once at build time, and
retrieval is a cosine top-k over the embedding matrix. The seam — `embed(query) ->
top-k ContentPda` — carries forward to a pgvector similarity query in M2 unchanged; only
the store behind `retrieve` swaps (numpy in-memory now, pgvector later).

`all_content_pdas()` feeds the hallucination guard: any output PDA absent from the whole
corpus is invented (roadmap task 8). Corpus completeness is roadmap open Q#1 — the seed
file is intentionally small; retrieval quality scales with the curriculum dropped into it.
"""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .ports.embeddings import EmbeddingProvider
from .schema import ContentPda

DATA_PATH = Path(__file__).parent / "data" / "fase6_corpus.json"


def _norm(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return stripped.casefold().strip()


@dataclass(frozen=True)
class CorpusEntry:
    campo: str
    content_pda: ContentPda

    def text(self) -> str:
        """Embedding input: the contenido plus its PDAs, so retrieval matches on both."""
        return self.content_pda.content + "\n" + "\n".join(self.content_pda.pdas)


def load_entries(path: Path = DATA_PATH) -> list[CorpusEntry]:
    """Read the JSON seed into typed entries (ignores the `_meta` note)."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [
        CorpusEntry(
            campo=item["campo"],
            content_pda=ContentPda(content=item["content"], pdas=item["pdas"]),
        )
        for item in raw["entries"]
    ]


def _l2_normalize(matrix: np.ndarray) -> np.ndarray:
    """Row-wise unit-length so a dot product is cosine similarity. Zero rows stay zero."""
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


class Corpus:
    """Embedded Fase 6 corpus with cosine top-k retrieval."""

    def __init__(
        self,
        entries: list[CorpusEntry],
        matrix: np.ndarray,
        embedder: EmbeddingProvider,
    ) -> None:
        self.entries = entries
        self._matrix = matrix  # (n, dim), L2-normalized
        self._embedder = embedder

    @classmethod
    def build(
        cls,
        embedder: EmbeddingProvider,
        entries: list[CorpusEntry] | None = None,
    ) -> "Corpus":
        entries = load_entries() if entries is None else entries
        vectors = np.asarray(embedder.embed([e.text() for e in entries]), dtype=np.float32)
        return cls(entries, _l2_normalize(vectors), embedder)

    def retrieve(self, query: str, k: int = 1, campo: str | None = None) -> list[ContentPda]:
        """Top-k contenidos by cosine similarity to `query`, optionally filtered by campo."""
        query_vec = np.asarray(self._embedder.embed([query]), dtype=np.float32)
        query_vec = _l2_normalize(query_vec)[0]
        sims = self._matrix @ query_vec

        results: list[ContentPda] = []
        for index in np.argsort(-sims):
            entry = self.entries[index]
            if campo is not None and _norm(entry.campo) != _norm(campo):
                continue
            results.append(entry.content_pda)
            if len(results) >= k:
                break
        return results

    def all_content_pdas(self) -> list[ContentPda]:
        """Every contenido in the corpus — the allowed set for the hallucination guard."""
        return [e.content_pda for e in self.entries]
