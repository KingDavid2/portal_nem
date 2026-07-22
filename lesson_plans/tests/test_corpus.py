"""Corpus retrieval — cosine top-k over a deterministic fake embedder so ranking is
pinned without the live endpoint. The real Qwen3-Embedding call is an integration concern.
"""

from __future__ import annotations

import unicodedata

import pytest

from lesson_plans.corpus import Corpus, load_entries
from lesson_plans.ports.llm import find_invented_pdas
from lesson_plans.schema import (
    ContentPda,
    Datos,
    Momento,
    Proyecto,
    Rubric,
    RubricCriterion,
    Session,
    Stage,
    Step,
)

# Keyword bag: each text -> counts over these terms. Distinct terms per corpus entry, so
# a query containing a term ranks that entry first (cosine over count vectors).
_VOCAB = ["independencia", "acentuacion", "argumentativo", "derechos", "materia", "salud"]


def _strip(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


class FakeEmbedder:
    name = "fake"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(_strip(t).count(term)) for term in _VOCAB] for t in texts]


@pytest.fixture
def corpus() -> Corpus:
    return Corpus.build(FakeEmbedder(), entries=load_entries())


def test_retrieve_ranks_the_matching_contenido_first(corpus: Corpus):
    hit = corpus.retrieve("La Independencia de México", k=1)
    assert len(hit) == 1
    assert "Independencia" in hit[0].content or any("Independencia" in p for p in hit[0].pdas)


def test_retrieve_matches_a_different_theme(corpus: Corpus):
    hit = corpus.retrieve("La producción de textos argumentativos", k=1)
    assert "argumentativo" in _strip(hit[0].content + " " + " ".join(hit[0].pdas))


def test_retrieve_campo_filter_excludes_other_campos(corpus: Corpus):
    hits = corpus.retrieve("materia y sus transformaciones", k=3, campo="Lenguajes")
    assert hits
    lenguajes_contents = {e.content_pda.content for e in corpus.entries if e.campo == "Lenguajes"}
    assert all(h.content in lenguajes_contents for h in hits)


def test_all_content_pdas_covers_every_entry(corpus: Corpus):
    assert len(corpus.all_content_pdas()) == len(corpus.entries)
    assert all(isinstance(c, ContentPda) for c in corpus.all_content_pdas())


def _proyecto_with(pdas: list[str]) -> Proyecto:
    return Proyecto(
        datos=Datos(school_name="X", grade="SEGUNDO", campo_formativo="C", date="HOY"),
        title="T",
        purpose="P",
        articulating_axes=[{"name": "Inclusión", "justification": "j"}],
        problem_or_theme="tema",
        contents_and_pdas=[ContentPda(content="c", pdas=pdas)],
        stages=[
            Stage(
                name="Planeación",
                momentos=[
                    Momento(
                        number=1,
                        name="Identificación",
                        sessions=[Session(duration_minutes=30, steps=[Step(number=1, dynamic="d")])],
                    )
                ],
            )
        ],
        rubric=Rubric(criteria=[RubricCriterion(criterion="Participación", levels=["A", "B", "C", "D"])]),
    )


def test_guard_against_corpus_flags_pda_absent_from_whole_corpus(corpus: Corpus):
    real = corpus.entries[0].content_pda.pdas[0]
    proyecto = _proyecto_with([real, "Este PDA no existe en ningún contenido del corpus."])
    invented = find_invented_pdas(proyecto, corpus.all_content_pdas())
    assert invented == ["Este PDA no existe en ningún contenido del corpus."]
