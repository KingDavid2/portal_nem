"""The golden references are committed text, not the gitignored source docx."""

from __future__ import annotations

import pytest

from .cases import CASES
from .golden import GOLDEN_DIR, golden_text


@pytest.mark.parametrize("field_id", sorted({case.field_id for case in CASES}))
def test_every_case_field_has_a_golden(field_id):
    assert golden_text(field_id).strip()


def test_golden_is_read_from_the_committed_copy():
    """`designs/examples/` is gitignored, so reading the docx at runtime would
    break on any other clone. The extracted text lives inside the package."""
    assert GOLDEN_DIR.is_dir()
    assert (GOLDEN_DIR / "ethics-nature-societies.md").is_file()


def test_unknown_field_is_a_key_error():
    with pytest.raises(KeyError):
        golden_text("no-such-field")


def test_golden_text_is_cached():
    assert golden_text("languages") is golden_text("languages")
