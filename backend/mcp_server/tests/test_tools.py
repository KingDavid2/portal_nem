"""RED/GREEN for the five read-only MCP tools (Slice 3 / S3b)."""

from __future__ import annotations

from dataclasses import asdict

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from lesson_plans.core.catalog import (
    CONTENTS,
    CROSS_CUTTING_THEMES,
    FIELDS,
    PDAS,
    SUBJECTS,
    _normalize,
)
from lesson_plans.models import GenerationUsage, LessonPlan
from lesson_plans.quota import current_period, format_period
from lesson_plans.serializers import (
    CatalogContentSerializer,
    CatalogFieldSerializer,
    CatalogGroupSerializer,
    CatalogSubjectSerializer,
    CatalogThemeSerializer,
    GenerationQuotaSerializer,
    LessonPlanSerializer,
)
from schools.models import Group, School, SchoolYear
from schools.serializers import GroupSerializer
from workspaces.models import Membership, Workspace
from workspaces.scope import workspace_scope

pytestmark = pytest.mark.django_db(transaction=True)
User = get_user_model()


@pytest.fixture
def membership_factory():
    def make(*, role=Membership.Role.MEMBER, workspace=None):
        workspace = workspace or Workspace.objects.create(type=Workspace.Type.GROUP)
        user = User.objects.create_user(
            email=f"mcp-tool-{Membership.objects.count()}@example.com",
            password="s3cret-pass",
        )
        return Membership.objects.create(user=user, workspace=workspace, role=role)

    return make


@pytest.fixture
def group_factory():
    def make(membership, *, grade=2, grupo="A"):
        school = School.objects.create(
            workspace=membership.workspace,
            name="Escuela Uno",
            level=School.Level.SECUNDARIA,
            cct="15DES0001A",
        )
        year = SchoolYear.objects.create(
            workspace=membership.workspace, school=school, label="2025-2026"
        )
        return Group.objects.create(
            workspace=membership.workspace,
            school_year=year,
            grado=grade,
            grupo=grupo,
        )

    return make


def _make_plan(membership, group):
    with workspace_scope(membership.workspace_id):
        return LessonPlan.objects.create(
            workspace=membership.workspace,
            group=group,
            campo="Lenguajes",
            grade="SEGUNDO",
            theme="La independencia",
        )


def test_list_groups_matches_catalog_payload(membership_factory, group_factory):
    """3.3"""
    from lesson_plans.serializers import catalog_group_payload
    from mcp_server.registry import dispatch

    membership = membership_factory()
    group = group_factory(membership)
    payload = dispatch("list_groups", {}, membership)["groups"][0]
    assert payload == catalog_group_payload(group)
    assert set(payload.keys()) == set(CatalogGroupSerializer().fields.keys())
    assert "school_year" not in payload and "workspace" not in payload
    assert set(payload.keys()) != set(GroupSerializer().fields.keys())


def test_list_and_get_match_lesson_plan_serializer(membership_factory, group_factory):
    """3.4"""
    from mcp_server.registry import dispatch

    membership = membership_factory()
    plan = _make_plan(membership, group_factory(membership))
    listed = dispatch("list_lesson_plans", {}, membership)["lesson_plans"][0]
    fetched = dispatch("get_lesson_plan", {"id": plan.pk}, membership)
    fields = set(LessonPlanSerializer().fields.keys())
    assert set(listed.keys()) == fields == set(fetched.keys())
    with workspace_scope(membership.workspace_id):
        expected = LessonPlanSerializer(plan).data
    assert listed == expected == fetched


def test_get_quota_matches_http_endpoint(membership_factory):
    """3.5"""
    from mcp_server.registry import dispatch

    membership = membership_factory()
    with workspace_scope(membership.workspace_id):
        GenerationUsage.objects.create(
            workspace=membership.workspace, period=current_period(), count=3
        )
    tool = dispatch("get_quota", {}, membership)
    assert set(tool.keys()) == {"period", "used", "limit", "remaining"}
    assert set(tool.keys()) == set(GenerationQuotaSerializer().fields.keys())
    client = APIClient()
    client.force_login(membership.user)
    client.credentials(HTTP_X_WORKSPACE_ID=str(membership.workspace_id))
    response = client.get("/api/lesson-plans/quota/")
    assert response.status_code == 200
    assert tool == dict(response.data)
    assert tool["period"] == format_period(current_period()) and tool["used"] == 3


def test_get_lesson_plan_indistinguishable_misses(membership_factory, group_factory):
    """3.6 — cross-workspace, nowhere, and malformed id share one error."""
    from mcp_server.registry import ToolNotFoundError, dispatch

    membership_a = membership_factory()
    membership_b = membership_factory()
    plan_b = _make_plan(membership_b, group_factory(membership_b))
    messages = []
    for args in ({"id": plan_b.pk}, {"id": 9_999_999}, {"id": "not-an-int"}):
        with pytest.raises(ToolNotFoundError) as exc_info:
            dispatch("get_lesson_plan", args, membership_a)
        messages.append(str(exc_info.value).encode("utf-8"))
    assert messages[0] == b"Lesson plan not found."
    assert messages[0] == messages[1] == messages[2]


def _content_payload(content):
    pda_by_id = {pda.id: pda for pda in PDAS}
    return {
        "id": content.id,
        "text": content.text,
        "pdas": [
            {"id": pda_id, "text": pda_by_id[pda_id].text}
            for pda_id in content.pda_ids
        ],
    }


def _whole_catalog_payload(*, field_id=None):
    if field_id is None:
        fields, subjects, contents = FIELDS, SUBJECTS, CONTENTS
    else:
        fields = tuple(f for f in FIELDS if f.id == field_id)
        subjects = tuple(s for s in SUBJECTS if s.field_id == field_id)
        contents = tuple(c for c in CONTENTS if c.field_id == field_id)
    return {
        "fields": CatalogFieldSerializer(
            [asdict(f) for f in fields], many=True
        ).data,
        "subjects": CatalogSubjectSerializer(
            [asdict(s) for s in subjects], many=True
        ).data,
        "cross_cutting_themes": CatalogThemeSerializer(
            [asdict(t) for t in CROSS_CUTTING_THEMES], many=True
        ).data,
        "contents": CatalogContentSerializer(
            [_content_payload(c) for c in contents], many=True
        ).data,
    }


def test_search_catalog_empty_query_returns_whole_catalog(membership_factory):
    """3.7 — empty query returns the whole catalog; bad field → ToolInputError."""
    from mcp_server.registry import ToolInputError, dispatch

    membership = membership_factory()
    payload = dispatch("search_catalog", {"query": "", "field": None}, membership)
    assert set(payload.keys()) == {
        "fields",
        "subjects",
        "cross_cutting_themes",
        "contents",
    }
    assert payload == _whole_catalog_payload()
    assert len(payload["fields"]) == len(FIELDS)
    assert len(payload["subjects"]) == len(SUBJECTS)
    assert len(payload["cross_cutting_themes"]) == len(CROSS_CUTTING_THEMES)
    assert len(payload["contents"]) == len(CONTENTS)

    with pytest.raises(ToolInputError):
        dispatch(
            "search_catalog",
            {"query": "", "field": "not-a-real-field"},
            membership,
        )


def test_search_catalog_normalize_match_and_whole_content(membership_factory):
    """3.7 — `_normalize` substring match; PDA hit renders the content whole."""
    from mcp_server.registry import dispatch

    membership = membership_factory()
    # Accent-/case-insensitive field name match via catalog._normalize.
    needle = "LENGUAJES"
    assert _normalize(needle) in _normalize(FIELDS[0].name)
    fields_hit = dispatch("search_catalog", {"query": needle}, membership)
    assert fields_hit["fields"] == CatalogFieldSerializer(
        [asdict(FIELDS[0])], many=True
    ).data
    assert fields_hit["subjects"] == []
    assert fields_hit["cross_cutting_themes"] == []
    assert fields_hit["contents"] == []

    subject_hit = dispatch("search_catalog", {"query": "Matemáticas"}, membership)
    assert [s["id"] for s in subject_hit["subjects"]] == ["mathematics"]
    theme_hit = dispatch("search_catalog", {"query": "Inclusión"}, membership)
    assert [t["id"] for t in theme_hit["cross_cutting_themes"]] == ["inclusion"]

    # PDA text match includes the parent content with every PDA, not a partial.
    target = next(c for c in CONTENTS if c.id == "ethics-independence")
    pda_needle = "napoleónica"
    assert any(_normalize(pda_needle) in _normalize(p.text) for p in PDAS)
    assert _normalize(pda_needle) not in _normalize(target.text)
    result = dispatch("search_catalog", {"query": pda_needle}, membership)
    assert result["contents"] == CatalogContentSerializer(
        [_content_payload(target)], many=True
    ).data
    assert len(result["contents"][0]["pdas"]) == len(target.pda_ids)


def test_search_catalog_empty_workspace_independent_of_rows(
    membership_factory, group_factory
):
    """3.8 — empty workspace still serves the frozen catalog."""
    from mcp_server.registry import dispatch

    empty = membership_factory()
    populated = membership_factory()
    _make_plan(populated, group_factory(populated))
    args = {"query": "independencia"}
    assert dispatch("search_catalog", args, empty) == dispatch(
        "search_catalog", args, populated
    )
    # Result is pure frozen-catalog data — no dependence on Group/LessonPlan rows.
    expected_content = next(c for c in CONTENTS if c.id == "ethics-independence")
    payload = dispatch("search_catalog", args, empty)
    assert payload["contents"] == CatalogContentSerializer(
        [_content_payload(expected_content)], many=True
    ).data


def test_no_shipped_tool_writes_any_row(membership_factory, group_factory):
    """3.9 — all five tools create, update, or delete no row."""
    from mcp_server.registry import ToolNotFoundError, dispatch

    membership = membership_factory()
    plan = _make_plan(membership, group_factory(membership))
    for name, args in (
        ("list_groups", {}),
        ("list_lesson_plans", {}),
        ("get_lesson_plan", {"id": plan.pk}),
        ("get_quota", {}),
        ("search_catalog", {"query": "lenguajes"}),
    ):
        with CaptureQueriesContext(connection) as ctx:
            dispatch(name, args, membership)
        writes = [
            q["sql"]
            for q in ctx.captured_queries
            if q["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
        ]
        assert writes == [], f"{name} wrote: {writes}"
    with CaptureQueriesContext(connection) as ctx:
        with pytest.raises(ToolNotFoundError):
            dispatch("get_lesson_plan", {"id": "bad"}, membership)
    writes = [
        q["sql"]
        for q in ctx.captured_queries
        if q["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
    ]
    assert writes == []
