"""School-structure MCP tools: teaching context, CRUD, confirm gate."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from schools.models import Group, School, SchoolYear
from students.models import Student
from workspaces.models import Membership, Workspace
from workspaces.scope import workspace_scope

pytestmark = pytest.mark.django_db(transaction=True)
User = get_user_model()


@pytest.fixture
def membership_factory():
    def make(*, role=Membership.Role.MEMBER, workspace=None):
        workspace = workspace or Workspace.objects.create(type=Workspace.Type.GROUP)
        user = User.objects.create_user(
            email=f"mcp-school-{Membership.objects.count()}@example.com",
            password="s3cret-pass",
        )
        return Membership.objects.create(user=user, workspace=workspace, role=role)

    return make


def _seed_year(membership, *, label="2025-2026", groups=(("2", "A"),)):
    school = School.objects.create(
        workspace=membership.workspace,
        name="Escuela Uno",
        level=School.Level.SECUNDARIA,
        cct="15DES0001A",
    )
    year = SchoolYear.objects.create(
        workspace=membership.workspace, school=school, label=label
    )
    created = []
    for grado, grupo in groups:
        created.append(
            Group.objects.create(
                workspace=membership.workspace,
                school_year=year,
                grado=int(grado),
                grupo=grupo,
            )
        )
    return school, year, created


def test_get_teaching_context_single_group_sets_default(membership_factory):
    from mcp_server.registry import dispatch

    membership = membership_factory()
    _, _, groups = _seed_year(membership, groups=(("2", "A"),))
    # Older cycle must not win.
    _seed_year(membership, label="2024-2025", groups=(("1", "B"),))

    payload = dispatch("get_teaching_context", {}, membership)
    assert payload["last_school_year_label"] == "2025-2026"
    assert payload["group_count"] == 1
    assert payload["default_group_id"] == groups[0].pk


def test_get_teaching_context_multiple_groups_null_default(membership_factory):
    from mcp_server.registry import dispatch

    membership = membership_factory()
    _seed_year(membership, groups=(("2", "A"), ("2", "B")))

    payload = dispatch("get_teaching_context", {}, membership)
    assert payload["group_count"] == 2
    assert payload["default_group_id"] is None


def test_create_student_persists(membership_factory):
    from mcp_server.registry import dispatch

    membership = membership_factory()
    _, _, groups = _seed_year(membership)
    group = groups[0]

    payload = dispatch(
        "create_student",
        {
            "group_id": group.pk,
            "first_name": "Pepe",
            "last_name_paternal": "Pérez",
        },
        membership,
    )
    assert payload["first_name"] == "Pepe"
    assert payload["last_name_paternal"] == "Pérez"
    assert payload["group"] == group.pk
    assert payload["school_year_label"] == "2025-2026"

    with workspace_scope(membership.workspace_id):
        assert Student.objects.filter(pk=payload["id"]).exists()


def test_create_student_orthography_clarification_does_not_write(membership_factory):
    from mcp_server.registry import dispatch

    membership = membership_factory()
    _seed_year(membership)

    result = dispatch(
        "create_student",
        {
            "first_name": "Pepe",
            "last_name_paternal": "Perez",
            "last_name_maternal": "Martinez",
        },
        membership,
    )
    assert result["status"] == "needs_orthography_clarification"
    assert result["suggested"]["last_name_paternal"] == "Pérez"
    assert result["suggested"]["last_name_maternal"] == "Martínez"
    with workspace_scope(membership.workspace_id):
        assert not Student.objects.filter(first_name="Pepe").exists()


def test_create_student_apply_suggested_accents(membership_factory):
    from mcp_server.registry import dispatch

    membership = membership_factory()
    _seed_year(membership)

    payload = dispatch(
        "create_student",
        {
            "first_name": "Pepe",
            "last_name_paternal": "Perez",
            "last_name_maternal": "Martinez",
            "apply_suggested": True,
        },
        membership,
    )
    assert payload["last_name_paternal"] == "Pérez"
    assert payload["last_name_maternal"] == "Martínez"
    with workspace_scope(membership.workspace_id):
        student = Student.objects.get(pk=payload["id"])
        assert student.last_name_paternal == "Pérez"


def test_create_student_keep_as_typed(membership_factory):
    from mcp_server.registry import dispatch

    membership = membership_factory()
    _seed_year(membership)

    payload = dispatch(
        "create_student",
        {
            "first_name": "Pepe",
            "last_name_paternal": "Perez",
            "keep_as_typed": True,
        },
        membership,
    )
    assert payload["last_name_paternal"] == "Perez"


def test_create_student_defaults_to_last_cycle_single_group(membership_factory):
    from mcp_server.registry import dispatch

    membership = membership_factory()
    _, _, old_groups = _seed_year(membership, label="2022-2023", groups=(("1", "A"),))
    _, _, new_groups = _seed_year(membership, label="2025-2026", groups=(("2", "B"),))

    payload = dispatch(
        "create_student",
        {
            "first_name": "Pepe",
            "last_name_paternal": "Pérez",
            "last_name_maternal": "Martínez",
        },
        membership,
    )
    assert payload["group"] == new_groups[0].pk
    assert payload["school_year_label"] == "2025-2026"
    assert payload["group"] != old_groups[0].pk


def test_create_student_rejects_group_from_older_cycle(membership_factory):
    from mcp_server.registry import ToolInputError, dispatch

    membership = membership_factory()
    _, _, old_groups = _seed_year(membership, label="2022-2023", groups=(("1", "A"),))
    _seed_year(membership, label="2025-2026", groups=(("2", "B"),))

    with pytest.raises(ToolInputError) as exc:
        dispatch(
            "create_student",
            {
                "group_id": old_groups[0].pk,
                "first_name": "Pepe",
                "last_name_paternal": "Pérez",
            },
            membership,
        )
    assert "2022-2023" in str(exc.value)
    assert "2025-2026" in str(exc.value)


def test_create_student_allows_explicit_older_cycle(membership_factory):
    from mcp_server.registry import dispatch

    membership = membership_factory()
    _, _, old_groups = _seed_year(membership, label="2022-2023", groups=(("1", "A"),))
    _seed_year(membership, label="2025-2026", groups=(("2", "B"),))

    payload = dispatch(
        "create_student",
        {
            "group_id": old_groups[0].pk,
            "school_year_label": "2022-2023",
            "first_name": "Pepe",
            "last_name_paternal": "Pérez",
        },
        membership,
    )
    assert payload["group"] == old_groups[0].pk
    assert payload["school_year_label"] == "2022-2023"


def test_delete_student_without_confirm_does_not_write(membership_factory):
    from mcp_server.registry import dispatch

    membership = membership_factory()
    _, _, groups = _seed_year(membership)
    with workspace_scope(membership.workspace_id):
        student = Student.objects.create(
            workspace=membership.workspace,
            group=groups[0],
            first_name="Ana",
            last_name_paternal="Lopez",
        )
        student_id = student.pk

    result = dispatch("delete_student", {"id": student_id}, membership)
    assert result["status"] == "needs_confirmation"
    assert result["action"] == "delete_student"

    with workspace_scope(membership.workspace_id):
        assert Student.objects.filter(pk=student_id).exists()


def test_delete_student_with_confirm_removes_row(membership_factory):
    from mcp_server.registry import dispatch

    membership = membership_factory()
    _, _, groups = _seed_year(membership)
    with workspace_scope(membership.workspace_id):
        student = Student.objects.create(
            workspace=membership.workspace,
            group=groups[0],
            first_name="Ana",
            last_name_paternal="Lopez",
        )
        student_id = student.pk

    result = dispatch(
        "delete_student", {"id": student_id, "confirm": True}, membership
    )
    assert result == {"status": "deleted", "id": student_id}

    with workspace_scope(membership.workspace_id):
        assert not Student.objects.filter(pk=student_id).exists()


def test_update_student_without_confirm_does_not_write(membership_factory):
    from mcp_server.registry import dispatch

    membership = membership_factory()
    _, _, groups = _seed_year(membership)
    with workspace_scope(membership.workspace_id):
        student = Student.objects.create(
            workspace=membership.workspace,
            group=groups[0],
            first_name="Ana",
            last_name_paternal="Lopez",
        )
        student_id = student.pk

    result = dispatch(
        "update_student",
        {"id": student_id, "first_name": "Anita"},
        membership,
    )
    assert result["status"] == "needs_confirmation"

    with workspace_scope(membership.workspace_id):
        assert Student.objects.get(pk=student_id).first_name == "Ana"


def test_create_student_denied_without_edit_content(membership_factory):
    from mcp_server.registry import ToolDenied, dispatch

    membership = membership_factory(role="ghost")
    _, _, groups = _seed_year(membership)

    with pytest.raises(ToolDenied):
        dispatch(
            "create_student",
            {
                "group_id": groups[0].pk,
                "first_name": "Pepe",
                "last_name_paternal": "Perez",
            },
            membership,
        )


def test_foreign_student_delete_is_not_found(membership_factory):
    from mcp_server.registry import ToolNotFoundError, dispatch

    a = membership_factory()
    b = membership_factory()
    _, _, groups_a = _seed_year(a)
    with workspace_scope(a.workspace_id):
        student = Student.objects.create(
            workspace=a.workspace,
            group=groups_a[0],
            first_name="X",
            last_name_paternal="Y",
        )
        student_id = student.pk

    with pytest.raises(ToolNotFoundError):
        dispatch(
            "delete_student",
            {"id": student_id, "confirm": True},
            b,
        )


def test_ephemeral_token_mint_and_revoke(membership_factory):
    from mcp_server.auth import resolve_membership
    from mcp_server.tokens import mint_ephemeral_token, revoke_token

    membership = membership_factory()
    raw, row = mint_ephemeral_token(membership, name="test")
    assert resolve_membership(raw) == membership
    revoke_token(row)
    assert resolve_membership(raw) is None
