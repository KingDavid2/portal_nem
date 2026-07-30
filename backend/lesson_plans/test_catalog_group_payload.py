"""RED/GREEN for `catalog_group_payload` (design D2 — one shape, no drift)."""

from __future__ import annotations

import pytest

from schools.models import Group, School, SchoolYear
from workspaces.models import Workspace

pytestmark = pytest.mark.django_db


def test_catalog_group_payload_matches_inline_catalog_shape():
    """3.1: helper returns the exact dict the catalog action used to build inline."""
    from lesson_plans.serializers import catalog_group_payload

    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    school = School.objects.create(
        workspace=workspace,
        name="Escuela Uno",
        level=School.Level.SECUNDARIA,
        cct="15DES0001A",
    )
    year = SchoolYear.objects.create(
        workspace=workspace, school=school, label="2025-2026"
    )
    group = Group.objects.create(
        workspace=workspace, school_year=year, grado=2, grupo="A"
    )
    assert catalog_group_payload(group) == {
        "id": group.pk,
        "label": "2° A",
        "grade": 2,
        "school_name": "Escuela Uno",
        "school_cct": "15DES0001A",
        "school_year_label": "2025-2026",
    }
