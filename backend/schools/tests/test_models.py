"""RED tests for School / SchoolYear / Group model shapes and constraints
(school-structure spec — Entity Field Shapes and Constraints).
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

pytestmark = pytest.mark.django_db


@pytest.fixture
def workspace():
    from workspaces.models import Workspace

    return Workspace.objects.create(type=Workspace.Type.GROUP)


def test_school_requires_name(workspace):
    from schools.models import School

    school = School(workspace=workspace, name="", level=School.Level.PRIMARIA)
    with pytest.raises(ValidationError):
        school.full_clean()


def test_school_cct_is_optional(workspace):
    from schools.models import School

    school = School(workspace=workspace, name="Escuela Uno", level=School.Level.PRIMARIA)
    school.full_clean()
    school.save()

    assert school.cct == ""


def test_school_level_restricted_to_enum(workspace):
    from schools.models import School

    school = School(workspace=workspace, name="Escuela Dos", level="universidad")
    with pytest.raises(ValidationError):
        school.full_clean()


def test_school_has_no_compound_unique_constraint(workspace):
    from workspaces.context import active_workspace

    from schools.models import School

    School.objects.create(workspace=workspace, name="Repetida", level=School.Level.PRIMARIA)
    # Two schools with the same name in the same workspace are allowed.
    School.objects.create(workspace=workspace, name="Repetida", level=School.Level.PRIMARIA)

    token = active_workspace.set(workspace.id)
    try:
        count = School.objects.filter(name="Repetida").count()
    finally:
        active_workspace.reset(token)

    assert count == 2


def test_school_year_unique_school_and_label(workspace):
    from schools.models import School, SchoolYear

    school = School.objects.create(
        workspace=workspace, name="Escuela Tres", level=School.Level.SECUNDARIA
    )
    SchoolYear.objects.create(workspace=workspace, school=school, label="2024-2025")

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            SchoolYear.objects.create(workspace=workspace, school=school, label="2024-2025")


def test_group_grado_rejects_out_of_range(workspace):
    from schools.models import Group, School, SchoolYear

    school = School.objects.create(
        workspace=workspace, name="Escuela Cuatro", level=School.Level.PREESCOLAR
    )
    school_year = SchoolYear.objects.create(
        workspace=workspace, school=school, label="2024-2025"
    )
    group = Group(workspace=workspace, school_year=school_year, grado=4, grupo="A")
    with pytest.raises(ValidationError):
        group.full_clean()


def test_group_unique_school_year_grado_grupo(workspace):
    from schools.models import Group, School, SchoolYear

    school = School.objects.create(
        workspace=workspace, name="Escuela Cinco", level=School.Level.PRIMARIA
    )
    school_year = SchoolYear.objects.create(
        workspace=workspace, school=school, label="2024-2025"
    )
    Group.objects.create(workspace=workspace, school_year=school_year, grado=1, grupo="A")

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Group.objects.create(
                workspace=workspace, school_year=school_year, grado=1, grupo="A"
            )
