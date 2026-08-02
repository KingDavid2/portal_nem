"""RED tests for Term / Activity / ActivityScore model shapes (grades spec —
Term Invariants, Activity Invariants and Tipo, ActivityScore Invariants).
"""

import datetime
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

pytestmark = pytest.mark.django_db


@pytest.fixture
def workspace():
    from workspaces.models import Workspace

    return Workspace.objects.create(type=Workspace.Type.GROUP)


@pytest.fixture
def school_year(workspace):
    from schools.models import School, SchoolYear

    school = School.objects.create(
        workspace=workspace, name="Escuela", level=School.Level.SECUNDARIA
    )
    return SchoolYear.objects.create(
        workspace=workspace, school=school, label="2024-2025"
    )


@pytest.fixture
def group(workspace, school_year):
    from schools.models import Group

    return Group.objects.create(
        workspace=workspace, school_year=school_year, grado=1, grupo="A"
    )


@pytest.fixture
def term(workspace, school_year):
    from grades.models import Term

    return Term.objects.create(workspace=workspace, school_year=school_year, number=1)


@pytest.fixture
def student(workspace, group):
    from students.models import Student

    return Student.objects.create(
        workspace=workspace,
        group=group,
        first_name="Ana",
        last_name_paternal="Perez",
    )


@pytest.fixture
def activity(workspace, group, term):
    from grades.models import Activity

    return Activity.objects.create(
        workspace=workspace,
        group=group,
        term=term,
        title="Ensayo",
        activity_type=Activity.ActivityType.TASK,
        due_date=datetime.date(2026, 8, 15),
        formative_field_id="languages",
        subject_ids=["spanish"],
        description="",
    )


def test_term_subclasses_scoped_model():
    from grades.models import Term
    from workspaces.models import ScopedModel

    assert issubclass(Term, ScopedModel)


def test_activity_subclasses_scoped_model():
    from grades.models import Activity
    from workspaces.models import ScopedModel

    assert issubclass(Activity, ScopedModel)


def test_activity_score_subclasses_scoped_model():
    from grades.models import ActivityScore
    from workspaces.models import ScopedModel

    assert issubclass(ActivityScore, ScopedModel)


def test_term_db_table():
    from grades.models import Term

    assert Term._meta.db_table == "grades_term"


def test_activity_db_table():
    from grades.models import Activity

    assert Activity._meta.db_table == "grades_activity"


def test_activity_score_db_table():
    from grades.models import ActivityScore

    assert ActivityScore._meta.db_table == "grades_activityscore"


def test_term_number_must_be_one_two_or_three(workspace, school_year):
    from grades.models import Term

    term = Term(workspace=workspace, school_year=school_year, number=4)
    with pytest.raises(ValidationError):
        term.full_clean()


def test_term_field_shapes(workspace, school_year):
    from grades.models import Term

    term = Term(workspace=workspace, school_year=school_year, number=2)
    term.full_clean()
    term.save()

    assert term.number == 2
    assert term.school_year_id == school_year.pk


def test_duplicate_term_school_year_number_raises(workspace, school_year):
    from grades.models import Term

    Term.objects.create(workspace=workspace, school_year=school_year, number=1)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Term.objects.create(workspace=workspace, school_year=school_year, number=1)


def test_activity_type_enum_values():
    from grades.models import Activity

    assert set(Activity.ActivityType.values) == {
        "task",
        "activity",
        "project",
        "exam",
    }


def test_activity_field_shapes(workspace, group, term):
    from grades.models import Activity

    activity = Activity(
        workspace=workspace,
        group=group,
        term=term,
        title="Proyecto final",
        activity_type=Activity.ActivityType.PROJECT,
        due_date=datetime.date(2026, 9, 1),
        formative_field_id="scientific-thinking",
        subject_ids=["mathematics", "biology"],
        description="Instrucciones",
    )
    activity.full_clean()
    activity.save()

    assert activity.title == "Proyecto final"
    assert activity.activity_type == "project"
    assert activity.subject_ids == ["mathematics", "biology"]
    assert activity.group_id == group.pk
    assert activity.term_id == term.pk


def test_activity_rejects_empty_subject_ids(workspace, group, term):
    from grades.models import Activity

    activity = Activity(
        workspace=workspace,
        group=group,
        term=term,
        title="Sin asignaturas",
        activity_type=Activity.ActivityType.TASK,
        due_date=datetime.date(2026, 8, 15),
        formative_field_id="languages",
        subject_ids=[],
    )
    with pytest.raises(ValidationError):
        activity.full_clean()


def test_activity_score_nullable_decimal_and_unique(workspace, activity, student):
    from grades.models import ActivityScore

    score = ActivityScore(
        workspace=workspace,
        activity=activity,
        student=student,
        score=None,
    )
    score.full_clean()
    score.save()
    assert score.score is None

    scored = ActivityScore(
        workspace=workspace,
        activity=activity,
        student=student,
        score=Decimal("8.5"),
    )
    # uniqueness blocks a second row for the same (activity, student)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            scored.save()


def test_activity_score_accepts_zero_point_zero(workspace, activity, student):
    from grades.models import ActivityScore

    score = ActivityScore(
        workspace=workspace,
        activity=activity,
        student=student,
        score=Decimal("0.0"),
    )
    score.full_clean()
    score.save()
    assert score.score == Decimal("0.0")


def test_deleting_student_with_scores_is_protected(workspace, activity, student):
    from grades.models import ActivityScore

    ActivityScore.objects.create(
        workspace=workspace,
        activity=activity,
        student=student,
        score=Decimal("9.0"),
    )

    with pytest.raises(ProtectedError):
        student.delete()


def test_deleting_activity_with_scores_is_protected(workspace, activity, student):
    from grades.models import ActivityScore

    ActivityScore.objects.create(
        workspace=workspace,
        activity=activity,
        student=student,
        score=Decimal("9.0"),
    )

    with pytest.raises(ProtectedError):
        activity.delete()
