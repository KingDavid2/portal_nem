"""RED/GREEN for the four workspace-scoped MCP tools (Slice 3).

`search_catalog` tests (3.7–3.8) deferred to feat/quizzy-p4-s3b-search-catalog.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from lesson_plans.models import GenerationUsage, LessonPlan
from lesson_plans.quota import current_period, format_period
from lesson_plans.serializers import (
    CatalogGroupSerializer,
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


def test_no_shipped_tool_writes_any_row(membership_factory, group_factory):
    """3.9 — four shipped tools; search_catalog deferred to S3b."""
    from mcp_server.registry import ToolNotFoundError, dispatch

    membership = membership_factory()
    plan = _make_plan(membership, group_factory(membership))
    for name, args in (
        ("list_groups", {}),
        ("list_lesson_plans", {}),
        ("get_lesson_plan", {"id": plan.pk}),
        ("get_quota", {}),
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
