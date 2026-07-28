"""Eval cases must stay resolvable against the frozen catalog.

These are the drift guards: if a content or PDA id is renamed in `catalog.py`,
the eval stops being a measurement of the same thing, and that has to fail here
rather than silently produce a scorecard against different curriculum text.
"""

from __future__ import annotations

import pytest

from ..core.catalog import FIELDS
from ..core.catalog_pdas import content_pdas_for
from .cases import CASES, case_by_id


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_case_resolves_against_the_frozen_catalog(case):
    groups = content_pdas_for(case.field_id, case.selections)

    assert groups, f"{case.id} resolved to no official content"
    assert all(group.pdas for group in groups)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_case_field_is_a_real_catalog_field(case):
    assert case.field_id in {field.id for field in FIELDS}


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_case_request_is_fully_populated(case):
    """`build_messages` interpolates every field; a blank one silently weakens
    the prompt instead of failing, so it is asserted here."""
    request = case.request

    assert request.campo and request.grade and request.theme and request.subject
    assert request.scenario and request.context_diagnosis
    assert request.duration_weeks > 0
    assert request.start_date and request.end_date
    assert request.cross_cutting_themes


def test_case_ids_are_unique():
    ids = [case.id for case in CASES]
    assert len(ids) == len(set(ids))


def test_case_by_id_returns_the_matching_case():
    assert case_by_id(CASES[0].id) is CASES[0]


def test_case_by_id_rejects_an_unknown_id():
    with pytest.raises(KeyError):
        case_by_id("no-such-case")


def test_cases_cover_both_fields_that_have_official_content():
    """Both catalog fields with verified curriculum text must be measured —
    otherwise a regression in one of them never shows up in a scorecard."""
    assert {case.field_id for case in CASES} == {"ethics-nature-societies", "languages"}
