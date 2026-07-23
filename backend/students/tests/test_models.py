"""RED tests for Student model shape (school-structure spec — Entity Field
Shapes and Constraints: curp indexed non-unique, group FK PROTECT).
"""

import pytest
from django.db.models import ProtectedError

pytestmark = pytest.mark.django_db


@pytest.fixture
def workspace():
    from workspaces.models import Workspace

    return Workspace.objects.create(type=Workspace.Type.GROUP)


@pytest.fixture
def group(workspace):
    from schools.models import Group, School, SchoolYear

    school = School.objects.create(
        workspace=workspace, name="Escuela", level=School.Level.PRIMARIA
    )
    school_year = SchoolYear.objects.create(
        workspace=workspace, school=school, label="2024-2025"
    )
    return Group.objects.create(
        workspace=workspace, school_year=school_year, grado=1, grupo="A"
    )


def test_curp_is_not_unique_two_students_may_share_it(workspace, group):
    from students.models import Student

    Student.objects.create(
        workspace=workspace,
        group=group,
        first_name="Ana",
        last_name_paternal="Perez",
        curp="AAAA000101HDFRRN01",
    )
    Student.objects.create(
        workspace=workspace,
        group=group,
        first_name="Beto",
        last_name_paternal="Perez",
        curp="AAAA000101HDFRRN01",
    )

    from workspaces.context import active_workspace

    token = active_workspace.set(workspace.id)
    try:
        count = Student.objects.filter(curp="AAAA000101HDFRRN01").count()
    finally:
        active_workspace.reset(token)

    assert count == 2


def test_curp_optional(workspace, group):
    from students.models import Student

    student = Student(
        workspace=workspace,
        group=group,
        first_name="Carla",
        last_name_paternal="Gomez",
    )
    student.full_clean()
    student.save()

    assert student.curp == ""


def test_group_deletion_with_students_is_protected(workspace, group):
    from students.models import Student

    Student.objects.create(
        workspace=workspace,
        group=group,
        first_name="Dani",
        last_name_paternal="Lopez",
    )

    with pytest.raises(ProtectedError):
        group.delete()
