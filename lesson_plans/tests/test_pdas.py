"""The hardcoded PDA fixture is the Phase A stand-in for RAG retrieval."""

from __future__ import annotations

import pytest

from lesson_plans.pdas import available_campos, pdas_for
from lesson_plans.schema import ContentPda


def test_lookup_is_case_and_accent_insensitive():
    a = pdas_for("ÉTICA, NATURALEZA Y SOCIEDADES")
    b = pdas_for("etica, naturaleza y sociedades")
    assert a == b


def test_fixture_returns_wellformed_contentpdas():
    groups = pdas_for("Ética, Naturaleza y Sociedades")
    assert groups
    assert all(isinstance(g, ContentPda) for g in groups)
    assert all(g.content.strip() for g in groups)
    assert all(g.pdas and all(p.strip() for p in g.pdas) for g in groups)


def test_unknown_campo_raises_keyerror_listing_options():
    with pytest.raises(KeyError):
        pdas_for("Campo Inexistente")


def test_available_campos_nonempty():
    campos = available_campos()
    assert campos
    assert "Ética, Naturaleza y Sociedades" in campos
