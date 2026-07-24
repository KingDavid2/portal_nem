"""Shared write-boundary validation for the planning endpoints.

Both `GET /api/lesson-plans/catalog/` and `POST /api/lesson-plans/` answer the
same two questions before they do anything else: is this group a secondary
school group, and is this a supported formative field? Keeping the checks and
their literal error strings here is what stops the read endpoint (which tells
the teacher what she may pick) and the write endpoint (which decides what she
may submit) from drifting apart.

The two endpoints only differ in which key carries the error — `field`/`group`
for the query-parameter action, `field_id`/`group` for the request body — so
every helper takes the key from its caller.
"""

from __future__ import annotations

from rest_framework.exceptions import ValidationError

from lesson_plans.core.catalog import Field, field_by_id
from schools.models import School

NON_SECONDARY_GROUP_ERROR = "The group must belong to a secondary school."
UNSUPPORTED_FIELD_ERROR = "Unsupported field id."
UNSUPPORTED_SUBJECT_ERROR = "Subject does not belong to the selected field."
UNSUPPORTED_METHODOLOGY_ERROR = "Unsupported methodology id."
UNSUPPORTED_THEME_ERROR = "Unsupported cross-cutting theme id."
EMPTY_THEMES_ERROR = "The cross-cutting theme ids must not be empty."
DUPLICATE_THEMES_ERROR = "The cross-cutting theme ids must not contain duplicates."
EMPTY_CONTENT_SELECTIONS_ERROR = "The content selections must not be empty."
DUPLICATE_CONTENT_SELECTIONS_ERROR = (
    "The content selections must not contain duplicate content ids."
)
UNSUPPORTED_CONTENT_ERROR = "Unsupported content id."
FOREIGN_PDA_ERROR = "PDA does not belong to the selected content."
DUPLICATE_PDAS_ERROR = "The pda ids must not contain duplicates."
END_DATE_BEFORE_START_DATE_ERROR = "The end date must not precede the start date."


def require_secondary_group(group, *, error_key: str) -> None:
    """Reject a group whose school is not a secundaria."""
    if group.school_year.school.level != School.Level.SECUNDARIA:
        raise ValidationError({error_key: NON_SECONDARY_GROUP_ERROR})


def resolve_field(field_id: str, *, error_key: str) -> Field:
    """Resolve a client-supplied formative-field id to its catalog record."""
    try:
        return field_by_id(field_id)
    except KeyError:
        raise ValidationError({error_key: UNSUPPORTED_FIELD_ERROR})
