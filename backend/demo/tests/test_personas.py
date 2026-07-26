"""Tests for the persona registry (demo.personas).

The registry is a frozen in-code catalogue of demo personas. These tests
verify the contract without touching the database — no DB needed.
"""

from __future__ import annotations

import pytest

from demo.personas import UnknownPersona, all, find, keys


def test_all_returns_a_tuple():
    result = all()
    assert isinstance(result, tuple)
    assert len(result) >= 1


def test_each_persona_has_non_empty_key():
    for persona in all():
        assert persona.key, f"Persona {persona!r} has an empty key"


def test_each_persona_has_non_empty_label():
    for persona in all():
        assert persona.label, f"Persona {persona.key!r} has an empty label"


def test_each_persona_has_non_empty_description():
    for persona in all():
        assert persona.description, f"Persona {persona.key!r} has an empty description"


def test_each_persona_has_at_least_one_feature():
    for persona in all():
        assert len(persona.features) >= 1, f"Persona {persona.key!r} has no features"


def test_keys_are_unique():
    persona_keys = [p.key for p in all()]
    assert len(persona_keys) == len(set(persona_keys)), "Duplicate keys found"


def test_keys_matches_all():
    assert keys() == tuple(p.key for p in all())


def test_find_returns_correct_persona():
    for persona in all():
        result = find(persona.key)
        assert result.key == persona.key
        assert result.label == persona.label


def test_find_raises_for_unknown_key():
    with pytest.raises(UnknownPersona):
        find("nope")


def test_find_raises_for_empty_key():
    with pytest.raises(UnknownPersona):
        find("")


def test_persona_is_frozen():
    """The Persona dataclass must be frozen — writes should raise."""
    persona = all()[0]
    with pytest.raises(Exception):
        persona.key = "tampered"


def test_persona_provisioner_is_a_dotted_path():
    """Each provisioner field should be a dotted import path string."""
    for persona in all():
        assert isinstance(persona.provisioner, str)
        assert "." in persona.provisioner, f"Persona {persona.key!r} provisioner is not a dotted path"