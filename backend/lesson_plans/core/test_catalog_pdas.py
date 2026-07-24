"""Tests for resolving stored selection ids into official curriculum text.

The point of this module is that the prompt sees exactly what the teacher
picked, verbatim from the catalog, and that anything unresolvable is a loud
`KeyError` (terminal in `tasks.py`) rather than a quietly narrowed selection.
"""

from __future__ import annotations

import pytest

from lesson_plans.core.catalog import PDAS, content_by_id, pda_by_id
from lesson_plans.core.catalog_pdas import content_pdas_for

ETHICS = "ethics-nature-societies"


def test_returns_verbatim_official_text_for_the_selection():
    groups = content_pdas_for(
        ETHICS,
        [{"content_id": "ethics-independence", "pda_ids": ["ethics-independence-graphics"]}],
    )

    assert len(groups) == 1
    assert groups[0].content == content_by_id(ETHICS, "ethics-independence").text
    assert groups[0].pdas == [pda_by_id(ETHICS, "ethics-independence-graphics").text]


def test_preserves_the_order_the_teacher_listed():
    """PDAs come back in selection order, not catalog order — the teacher's
    sequencing is part of what she chose."""
    catalog_order = [pda.id for pda in PDAS if pda.content_id == "ethics-independence"]
    reversed_order = list(reversed(catalog_order))

    groups = content_pdas_for(
        ETHICS, [{"content_id": "ethics-independence", "pda_ids": reversed_order}]
    )

    assert groups[0].pdas == [pda_by_id(ETHICS, pda_id).text for pda_id in reversed_order]


def test_unknown_content_id_raises_key_error():
    with pytest.raises(KeyError):
        content_pdas_for(ETHICS, [{"content_id": "no-such-content", "pda_ids": []}])


def test_unknown_pda_id_raises_key_error():
    with pytest.raises(KeyError):
        content_pdas_for(
            ETHICS,
            [{"content_id": "ethics-independence", "pda_ids": ["no-such-pda"]}],
        )


def test_pda_from_another_field_raises_key_error():
    with pytest.raises(KeyError):
        content_pdas_for(
            ETHICS,
            [{"content_id": "ethics-independence", "pda_ids": ["languages-accentuation"]}],
        )
