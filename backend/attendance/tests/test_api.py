"""RED HTTP tests for attendance DRF surface (attendance spec — Roster Read
Endpoint, Bulk Upsert Endpoint; authorization spec — Attendance Endpoints Map
Custom Actions to Capabilities).
"""

from __future__ import annotations

import datetime
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture
def membership_factory():
    from workspaces.models import Membership, Workspace

    def make(role="member", workspace=None):
        user = User.objects.create_user(
            email=f"{role}-{Workspace.objects.count()}@example.com",
            password="s3cret-pass",
        )
        workspace = workspace or Workspace.objects.create(type=Workspace.Type.GROUP)
        return Membership.objects.create(user=user, workspace=workspace, role=role)

    return make


@pytest.fixture
def api_client_for():
    def make(membership):
        client = APIClient()
        client.force_login(membership.user)
        client.credentials(HTTP_X_WORKSPACE_ID=str(membership.workspace_id))
        return client

    return make


@pytest.fixture
def group_for(api_client_for):
    def make(membership):
        client = api_client_for(membership)
        school_resp = client.post(
            "/api/schools/", {"name": "Escuela Uno", "cct": "", "level": "primaria"}
        )
        school_year_resp = client.post(
            "/api/school-years/",
            {"school": school_resp.data["id"], "label": "2024-2025"},
        )
        group_resp = client.post(
            "/api/groups/",
            {"school_year": school_year_resp.data["id"], "grado": 1, "grupo": "A"},
        )
        return group_resp.data["id"]

    return make


@pytest.fixture
def student_for(api_client_for):
    def make(membership, group_id, *, first_name="Ana", last_name_paternal="Perez"):
        client = api_client_for(membership)
        response = client.post(
            "/api/students/",
            {
                "group": group_id,
                "first_name": first_name,
                "last_name_paternal": last_name_paternal,
            },
        )
        assert response.status_code == 201
        return response.data["id"]

    return make


def test_roster_merges_saved_and_unsaved_defaults_present(
    membership_factory, api_client_for, group_for, student_for
):
    from attendance.models import AttendanceRecord

    membership = membership_factory("member")
    group_id = group_for(membership)
    student_a = student_for(membership, group_id, first_name="Ana")
    student_for(membership, group_id, first_name="Beto")
    AttendanceRecord.objects.create(
        workspace=membership.workspace,
        student_id=student_a,
        date=datetime.date(2026, 8, 1),
        status=AttendanceRecord.Status.ABSENT,
        notes="Enferma",
    )
    client = api_client_for(membership)

    response = client.get(
        "/api/attendance/roster/",
        {"group": group_id, "date": "2026-08-01"},
    )

    assert response.status_code == 200
    by_name = {row["first_name"]: row for row in response.data}
    assert by_name["Ana"]["status"] == "absent"
    assert by_name["Ana"]["notes"] == "Enferma"
    assert by_name["Beto"]["status"] == "present"
    assert by_name["Beto"]["notes"] == ""


def test_roster_empty_group(membership_factory, api_client_for, group_for):
    membership = membership_factory("member")
    group_id = group_for(membership)
    client = api_client_for(membership)

    response = client.get(
        "/api/attendance/roster/",
        {"group": group_id, "date": "2026-08-01"},
    )

    assert response.status_code == 200
    assert response.data == []


def test_roster_foreign_workspace_group_returns_404(
    membership_factory, api_client_for, group_for
):
    membership_a = membership_factory("member")
    membership_b = membership_factory("member")
    foreign_group = group_for(membership_b)
    client_a = api_client_for(membership_a)

    response = client_a.get(
        "/api/attendance/roster/",
        {"group": foreign_group, "date": "2026-08-01"},
    )

    assert response.status_code == 404


def test_roster_missing_params_returns_400(membership_factory, api_client_for, group_for):
    membership = membership_factory("member")
    group_id = group_for(membership)
    client = api_client_for(membership)

    assert client.get("/api/attendance/roster/").status_code == 400
    assert (
        client.get("/api/attendance/roster/", {"group": group_id}).status_code == 400
    )
    assert client.get("/api/attendance/roster/", {"date": "2026-08-01"}).status_code == 400


def test_roster_requires_workspace_header(membership_factory, group_for):
    membership = membership_factory("member")
    group_id = group_for(membership)
    client = APIClient()
    client.force_login(membership.user)

    response = client.get(
        "/api/attendance/roster/",
        {"group": group_id, "date": "2026-08-01"},
    )

    assert response.status_code == 403


def test_bulk_upsert_persists_all_entries(
    membership_factory, api_client_for, group_for, student_for
):
    membership = membership_factory("member")
    group_id = group_for(membership)
    student_a = student_for(membership, group_id, first_name="Ana")
    student_b = student_for(membership, group_id, first_name="Beto")
    client = api_client_for(membership)

    response = client.put(
        "/api/attendance/bulk/",
        {
            "group": group_id,
            "date": "2026-08-01",
            "entries": [
                {"student": student_a, "status": "absent", "notes": "A"},
                {"student": student_b, "status": "late", "notes": "B"},
            ],
        },
        format="json",
    )

    assert response.status_code == 200
    roster = client.get(
        "/api/attendance/roster/",
        {"group": group_id, "date": "2026-08-01"},
    )
    by_name = {row["first_name"]: row for row in roster.data}
    assert by_name["Ana"]["status"] == "absent"
    assert by_name["Beto"]["status"] == "late"


def test_bulk_rejects_student_not_in_group_no_partial_write(
    membership_factory, api_client_for, group_for, student_for
):
    from attendance.models import AttendanceRecord

    membership = membership_factory("member")
    other = membership_factory("member")
    group_id = group_for(membership)
    foreign_group = group_for(other)
    student_in_group = student_for(membership, group_id, first_name="Ana")
    outsider = student_for(other, foreign_group, first_name="Carla")
    client = api_client_for(membership)

    response = client.put(
        "/api/attendance/bulk/",
        {
            "group": group_id,
            "date": "2026-08-01",
            "entries": [
                {"student": student_in_group, "status": "present", "notes": ""},
                {"student": outsider, "status": "absent", "notes": ""},
            ],
        },
        format="json",
    )

    assert response.status_code == 400
    assert AttendanceRecord.objects.count() == 0


def test_bulk_rejects_invalid_status(
    membership_factory, api_client_for, group_for, student_for
):
    from attendance.models import AttendanceRecord

    membership = membership_factory("member")
    group_id = group_for(membership)
    student_id = student_for(membership, group_id)
    client = api_client_for(membership)

    response = client.put(
        "/api/attendance/bulk/",
        {
            "group": group_id,
            "date": "2026-08-01",
            "entries": [{"student": student_id, "status": "tardy", "notes": ""}],
        },
        format="json",
    )

    assert response.status_code == 400
    assert AttendanceRecord.objects.count() == 0


def test_bulk_rejects_notes_over_500_chars(
    membership_factory, api_client_for, group_for, student_for
):
    from attendance.models import AttendanceRecord

    membership = membership_factory("member")
    group_id = group_for(membership)
    student_id = student_for(membership, group_id)
    client = api_client_for(membership)

    response = client.put(
        "/api/attendance/bulk/",
        {
            "group": group_id,
            "date": "2026-08-01",
            "entries": [
                {"student": student_id, "status": "present", "notes": "x" * 501},
            ],
        },
        format="json",
    )

    assert response.status_code == 400
    assert AttendanceRecord.objects.count() == 0


def test_roster_capability_maps_to_view_workspace(membership_factory, monkeypatch):
    from attendance.views import AttendanceRosterView
    from workspaces import permissions

    membership = membership_factory("member")
    calls = []

    def fake_has_permission(passed_membership, action):
        calls.append((passed_membership, action))
        return True

    monkeypatch.setattr(permissions, "has_permission", fake_has_permission)

    class FakeRequest:
        pass

    request = FakeRequest()
    request.membership = membership
    view = AttendanceRosterView()
    view.action = "roster"

    assert permissions.WorkspacePermission().has_permission(request, view) is True
    assert calls == [(membership, "view_workspace")]


def test_bulk_capability_maps_to_edit_content(membership_factory, monkeypatch):
    from attendance.views import AttendanceBulkView
    from workspaces import permissions

    membership = membership_factory("member")
    calls = []

    def fake_has_permission(passed_membership, action):
        calls.append((passed_membership, action))
        return True

    monkeypatch.setattr(permissions, "has_permission", fake_has_permission)

    class FakeRequest:
        pass

    request = FakeRequest()
    request.membership = membership
    view = AttendanceBulkView()
    view.action = "bulk"

    assert permissions.WorkspacePermission().has_permission(request, view) is True
    assert calls == [(membership, "edit_content")]


def test_bulk_denied_without_edit_content(
    membership_factory, api_client_for, group_for, student_for
):
    from attendance.models import AttendanceRecord

    membership = membership_factory("member")
    group_id = group_for(membership)
    student_id = student_for(membership, group_id)
    membership.role = "no-capabilities-role"
    membership.save(update_fields=["role"])
    client = api_client_for(membership)

    response = client.put(
        "/api/attendance/bulk/",
        {
            "group": group_id,
            "date": "2026-08-01",
            "entries": [{"student": student_id, "status": "present", "notes": ""}],
        },
        format="json",
    )

    assert response.status_code == 403
    assert AttendanceRecord.objects.count() == 0


def test_week_rejects_non_monday(membership_factory, api_client_for, group_for):
    membership = membership_factory("member")
    group_id = group_for(membership)
    client = api_client_for(membership)

    response = client.get(
        "/api/attendance/week/",
        {"group": group_id, "week_start": "2026-08-01"},  # Saturday
    )

    assert response.status_code == 400


def test_week_returns_matrix_with_defaults(
    membership_factory, api_client_for, group_for, student_for
):
    from attendance.models import AttendanceRecord

    membership = membership_factory("member")
    group_id = group_for(membership)
    student_a = student_for(membership, group_id, first_name="Ana")
    student_for(membership, group_id, first_name="Beto")
    AttendanceRecord.objects.create(
        workspace=membership.workspace,
        student_id=student_a,
        date=datetime.date(2026, 7, 27),
        status=AttendanceRecord.Status.ABSENT,
        notes="Enferma",
    )
    client = api_client_for(membership)

    response = client.get(
        "/api/attendance/week/",
        {"group": group_id, "week_start": "2026-07-27"},
    )

    assert response.status_code == 200
    assert response.data["week_start"] == "2026-07-27"
    assert response.data["dates"] == [
        "2026-07-27",
        "2026-07-28",
        "2026-07-29",
        "2026-07-30",
        "2026-07-31",
    ]
    by_name = {row["first_name"]: row for row in response.data["students"]}
    assert by_name["Ana"]["days"]["2026-07-27"] == "absent"
    assert by_name["Ana"]["days"]["2026-07-28"] == "present"
    assert by_name["Beto"]["days"]["2026-07-27"] == "present"
    assert "curp" not in by_name["Ana"]
    assert "notes" not in by_name["Ana"]


def test_week_foreign_workspace_group_returns_404(
    membership_factory, api_client_for, group_for
):
    membership_a = membership_factory("member")
    membership_b = membership_factory("member")
    foreign_group = group_for(membership_b)
    client_a = api_client_for(membership_a)

    response = client_a.get(
        "/api/attendance/week/",
        {"group": foreign_group, "week_start": "2026-07-27"},
    )

    assert response.status_code == 404


def test_week_bulk_persists_and_preserves_notes(
    membership_factory, api_client_for, group_for, student_for
):
    from attendance.models import AttendanceRecord

    membership = membership_factory("member")
    group_id = group_for(membership)
    student_id = student_for(membership, group_id, first_name="Ana")
    AttendanceRecord.objects.create(
        workspace=membership.workspace,
        student_id=student_id,
        date=datetime.date(2026, 7, 27),
        status=AttendanceRecord.Status.ABSENT,
        notes="Keep me",
    )
    client = api_client_for(membership)

    response = client.put(
        "/api/attendance/week/bulk/",
        {
            "group": group_id,
            "week_start": "2026-07-27",
            "entries": [
                {"student": student_id, "date": "2026-07-27", "status": "late"},
                {"student": student_id, "date": "2026-07-28", "status": "excused"},
            ],
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.data["saved"] == 2

    week = client.get(
        "/api/attendance/week/",
        {"group": group_id, "week_start": "2026-07-27"},
    )
    assert week.status_code == 200
    days = week.data["students"][0]["days"]
    assert days["2026-07-27"] == "late"
    assert days["2026-07-28"] == "excused"

    daily = client.get(
        "/api/attendance/roster/",
        {"group": group_id, "date": "2026-07-27"},
    )
    assert daily.data[0]["notes"] == "Keep me"
    assert daily.data[0]["status"] == "late"


def test_week_bulk_rejects_date_outside_window(
    membership_factory, api_client_for, group_for, student_for
):
    from attendance.models import AttendanceRecord

    membership = membership_factory("member")
    group_id = group_for(membership)
    student_id = student_for(membership, group_id)
    client = api_client_for(membership)

    response = client.put(
        "/api/attendance/week/bulk/",
        {
            "group": group_id,
            "week_start": "2026-07-27",
            "entries": [
                {"student": student_id, "date": "2026-08-01", "status": "present"},
            ],
        },
        format="json",
    )

    assert response.status_code == 400
    assert AttendanceRecord.objects.count() == 0


def test_week_bulk_rejects_student_not_in_group_no_partial_write(
    membership_factory, api_client_for, group_for, student_for
):
    from attendance.models import AttendanceRecord

    membership = membership_factory("member")
    other = membership_factory("member")
    group_id = group_for(membership)
    foreign_group = group_for(other)
    student_in_group = student_for(membership, group_id, first_name="Ana")
    outsider = student_for(other, foreign_group, first_name="Carla")
    client = api_client_for(membership)

    response = client.put(
        "/api/attendance/week/bulk/",
        {
            "group": group_id,
            "week_start": "2026-07-27",
            "entries": [
                {"student": student_in_group, "date": "2026-07-27", "status": "present"},
                {"student": outsider, "date": "2026-07-27", "status": "absent"},
            ],
        },
        format="json",
    )

    assert response.status_code == 400
    assert AttendanceRecord.objects.count() == 0


def test_week_capability_maps_to_view_workspace(membership_factory, monkeypatch):
    from attendance.views import AttendanceWeekView
    from workspaces import permissions

    membership = membership_factory("member")
    calls = []

    def fake_has_permission(passed_membership, action):
        calls.append((passed_membership, action))
        return True

    monkeypatch.setattr(permissions, "has_permission", fake_has_permission)

    class FakeRequest:
        pass

    request = FakeRequest()
    request.membership = membership
    view = AttendanceWeekView()
    view.action = "week"

    assert permissions.WorkspacePermission().has_permission(request, view) is True
    assert calls == [(membership, "view_workspace")]


def test_week_bulk_capability_maps_to_edit_content(membership_factory, monkeypatch):
    from attendance.views import AttendanceWeekBulkView
    from workspaces import permissions

    membership = membership_factory("member")
    calls = []

    def fake_has_permission(passed_membership, action):
        calls.append((passed_membership, action))
        return True

    monkeypatch.setattr(permissions, "has_permission", fake_has_permission)

    class FakeRequest:
        pass

    request = FakeRequest()
    request.membership = membership
    view = AttendanceWeekBulkView()
    view.action = "week_bulk"

    assert permissions.WorkspacePermission().has_permission(request, view) is True
    assert calls == [(membership, "edit_content")]
