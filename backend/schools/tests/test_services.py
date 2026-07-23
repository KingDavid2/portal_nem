"""RED tests for schools/services.py (school-structure spec — CRUD Gated by
edit_content Capability; Cross-Entity Workspace Consistency Validation).
"""

import pytest
from django.core.exceptions import PermissionDenied

pytestmark = pytest.mark.django_db


@pytest.fixture
def membership_factory():
    from django.contrib.auth import get_user_model

    from workspaces.models import Membership, Workspace

    User = get_user_model()

    def make(role, workspace=None):
        user = User.objects.create_user(
            email=f"{role}-{Workspace.objects.count()}@example.com",
            password="s3cret-pass",
        )
        workspace = workspace or Workspace.objects.create(type=Workspace.Type.GROUP)
        return Membership.objects.create(user=user, workspace=workspace, role=role)

    return make


@pytest.fixture
def member_membership(membership_factory):
    return membership_factory("member")


@pytest.fixture
def viewer_membership(membership_factory):
    """A membership whose role only carries view_workspace, not edit_content.

    The capability matrix currently grants edit_content to member/admin/
    owner; there is no "viewer-only" role yet, so simulate denial via a
    fake role lacking every capability.
    """
    from workspaces.models import Membership, Workspace

    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(email="viewer@example.com", password="s3cret-pass")
    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    membership = Membership.objects.create(user=user, workspace=workspace, role="member")
    membership.role = "no-capabilities-role"
    return membership


# --- School --------------------------------------------------------------


def test_create_school_success(member_membership):
    from schools.services import create_school

    school = create_school(
        membership=member_membership, name="Escuela Uno", cct="", level="primaria"
    )

    assert school.workspace_id == member_membership.workspace_id
    assert school.name == "Escuela Uno"


def test_create_school_denied_without_edit_content(viewer_membership):
    from schools.services import create_school

    with pytest.raises(PermissionDenied):
        create_school(
            membership=viewer_membership, name="Escuela Uno", cct="", level="primaria"
        )


def test_update_school_denied_without_edit_content(member_membership, viewer_membership):
    from schools.services import create_school, update_school

    school = create_school(
        membership=member_membership, name="Escuela Uno", cct="", level="primaria"
    )

    with pytest.raises(PermissionDenied):
        update_school(membership=viewer_membership, school=school, name="Nuevo Nombre")


def test_update_school_denied_cross_workspace(member_membership, membership_factory):
    from schools.services import create_school, update_school

    school = create_school(
        membership=member_membership, name="Escuela Uno", cct="", level="primaria"
    )
    other_membership = membership_factory("member")

    with pytest.raises(ValueError):
        update_school(membership=other_membership, school=school, name="Nuevo Nombre")


def test_delete_school_success(member_membership):
    from schools.models import School
    from schools.services import create_school, delete_school

    school = create_school(
        membership=member_membership, name="Escuela Uno", cct="", level="primaria"
    )
    delete_school(membership=member_membership, school=school)

    assert not School.objects.filter(pk=school.pk).exists()


# --- SchoolYear ------------------------------------------------------------


def test_create_school_year_success(member_membership):
    from schools.services import create_school, create_school_year

    school = create_school(
        membership=member_membership, name="Escuela Uno", cct="", level="primaria"
    )
    school_year = create_school_year(
        membership=member_membership, school=school, label="2024-2025"
    )

    assert school_year.workspace_id == member_membership.workspace_id
    assert school_year.school_id == school.pk


def test_create_school_year_denied_when_school_in_other_workspace(
    member_membership, membership_factory
):
    from schools.services import create_school, create_school_year

    other_membership = membership_factory("member")
    school = create_school(
        membership=other_membership, name="Escuela Ajena", cct="", level="primaria"
    )

    with pytest.raises(ValueError):
        create_school_year(membership=member_membership, school=school, label="2024-2025")


def test_update_school_year_success(member_membership):
    from schools.services import create_school, create_school_year, update_school_year

    school = create_school(
        membership=member_membership, name="Escuela Uno", cct="", level="primaria"
    )
    school_year = create_school_year(
        membership=member_membership, school=school, label="2024-2025"
    )
    updated = update_school_year(
        membership=member_membership, school_year=school_year, label="2025-2026"
    )

    assert updated.label == "2025-2026"


def test_delete_school_year_success(member_membership):
    from schools.models import SchoolYear
    from schools.services import create_school, create_school_year, delete_school_year

    school = create_school(
        membership=member_membership, name="Escuela Uno", cct="", level="primaria"
    )
    school_year = create_school_year(
        membership=member_membership, school=school, label="2024-2025"
    )
    delete_school_year(membership=member_membership, school_year=school_year)

    assert not SchoolYear.objects.filter(pk=school_year.pk).exists()


# --- Group -------------------------------------------------------------------


def test_create_group_success(member_membership):
    from schools.services import create_group, create_school, create_school_year

    school = create_school(
        membership=member_membership, name="Escuela Uno", cct="", level="primaria"
    )
    school_year = create_school_year(
        membership=member_membership, school=school, label="2024-2025"
    )
    group = create_group(
        membership=member_membership, school_year=school_year, grado=1, grupo="A"
    )

    assert group.workspace_id == member_membership.workspace_id
    assert group.school_year_id == school_year.pk


def test_create_group_denied_when_school_year_in_other_workspace(
    member_membership, membership_factory
):
    from schools.services import create_group, create_school, create_school_year

    other_membership = membership_factory("member")
    school = create_school(
        membership=other_membership, name="Escuela Ajena", cct="", level="primaria"
    )
    school_year = create_school_year(
        membership=other_membership, school=school, label="2024-2025"
    )

    with pytest.raises(ValueError):
        create_group(
            membership=member_membership, school_year=school_year, grado=1, grupo="A"
        )


def test_update_group_success(member_membership):
    from schools.services import create_group, create_school, create_school_year, update_group

    school = create_school(
        membership=member_membership, name="Escuela Uno", cct="", level="primaria"
    )
    school_year = create_school_year(
        membership=member_membership, school=school, label="2024-2025"
    )
    group = create_group(
        membership=member_membership, school_year=school_year, grado=1, grupo="A"
    )
    updated = update_group(membership=member_membership, group=group, grupo="B")

    assert updated.grupo == "B"


def test_delete_group_success(member_membership):
    from schools.models import Group
    from schools.services import create_group, create_school, create_school_year, delete_group

    school = create_school(
        membership=member_membership, name="Escuela Uno", cct="", level="primaria"
    )
    school_year = create_school_year(
        membership=member_membership, school=school, label="2024-2025"
    )
    group = create_group(
        membership=member_membership, school_year=school_year, grado=1, grupo="A"
    )
    delete_group(membership=member_membership, group=group)

    assert not Group.objects.filter(pk=group.pk).exists()
