"""RED tests for students/services.py (school-structure spec — CRUD Gated by
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
def viewer_membership():
    from django.contrib.auth import get_user_model

    from workspaces.models import Membership, Workspace

    User = get_user_model()
    user = User.objects.create_user(email="viewer@example.com", password="s3cret-pass")
    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    membership = Membership.objects.create(user=user, workspace=workspace, role="member")
    membership.role = "no-capabilities-role"
    return membership


@pytest.fixture
def group_factory(member_membership):
    from schools.services import create_group, create_school, create_school_year

    def make(membership=member_membership):
        school = create_school(
            membership=membership, name="Escuela Uno", cct="", level="primaria"
        )
        school_year = create_school_year(
            membership=membership, school=school, label="2024-2025"
        )
        return create_group(membership=membership, school_year=school_year, grado=1, grupo="A")

    return make


def test_create_student_success(member_membership, group_factory):
    from students.services import create_student

    group = group_factory()
    student = create_student(
        membership=member_membership,
        group=group,
        first_name="Ana",
        last_name_paternal="Perez",
    )

    assert student.workspace_id == member_membership.workspace_id
    assert student.group_id == group.pk


def test_create_student_denied_without_edit_content(viewer_membership, group_factory):
    from students.services import create_student

    group = group_factory()

    with pytest.raises(PermissionDenied):
        create_student(
            membership=viewer_membership,
            group=group,
            first_name="Ana",
            last_name_paternal="Perez",
        )


def test_create_student_denied_when_group_in_other_workspace(
    member_membership, membership_factory, group_factory
):
    from students.services import create_student

    other_membership = membership_factory("member")
    group = group_factory(membership=other_membership)

    with pytest.raises(ValueError):
        create_student(
            membership=member_membership,
            group=group,
            first_name="Ana",
            last_name_paternal="Perez",
        )


def test_update_student_success(member_membership, group_factory):
    from students.services import create_student, update_student

    group = group_factory()
    student = create_student(
        membership=member_membership,
        group=group,
        first_name="Ana",
        last_name_paternal="Perez",
    )
    updated = update_student(
        membership=member_membership, student=student, first_name="Ana Maria"
    )

    assert updated.first_name == "Ana Maria"


def test_update_student_denied_cross_workspace(
    member_membership, membership_factory, group_factory
):
    from students.services import create_student, update_student

    group = group_factory()
    student = create_student(
        membership=member_membership,
        group=group,
        first_name="Ana",
        last_name_paternal="Perez",
    )
    other_membership = membership_factory("member")

    with pytest.raises(ValueError):
        update_student(membership=other_membership, student=student, first_name="Nope")


def test_delete_student_success(member_membership, group_factory):
    from students.models import Student
    from students.services import create_student, delete_student

    group = group_factory()
    student = create_student(
        membership=member_membership,
        group=group,
        first_name="Ana",
        last_name_paternal="Perez",
    )
    delete_student(membership=member_membership, student=student)

    assert not Student.objects.filter(pk=student.pk).exists()
