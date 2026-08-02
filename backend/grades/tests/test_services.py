"""RED tests for grades/services.py (grades spec — Term ensure_terms, Catalog
Validation, list filters/stats, matrix null≠0, bulk atomic upsert).
"""

import datetime
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

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
        role_value = role if isinstance(role, Membership.Role) else Membership.Role(role)
        return Membership.objects.create(
            user=user, workspace=workspace, role=role_value
        )

    return make


@pytest.fixture
def member_membership(membership_factory):
    from workspaces.models import Membership

    return membership_factory(Membership.Role.MEMBER)


@pytest.fixture
def school_year_factory(member_membership):
    from schools.services import create_school, create_school_year

    def make(membership=member_membership):
        school = create_school(
            membership=membership,
            name="Escuela Uno",
            cct="",
            level="secundaria",
        )
        return create_school_year(
            membership=membership, school=school, label="2024-2025"
        )

    return make


@pytest.fixture
def group_factory(member_membership, school_year_factory):
    from schools.services import create_group

    def make(membership=member_membership, school_year=None):
        school_year = school_year or school_year_factory(membership=membership)
        return create_group(
            membership=membership,
            school_year=school_year,
            grado=1,
            grupo="A",
        )

    return make


@pytest.fixture
def student_factory(member_membership, group_factory):
    from students.services import create_student

    def make(*, membership=member_membership, group=None, first_name="Ana", **kwargs):
        group = group or group_factory(membership=membership)
        return create_student(
            membership=membership,
            group=group,
            first_name=first_name,
            last_name_paternal=kwargs.get("last_name_paternal", "Perez"),
        )

    return make


def test_ensure_terms_idempotent_seeds_one_through_three(
    member_membership, school_year_factory
):
    from grades.models import Term
    from grades.services import ensure_terms
    from workspaces.context import active_workspace

    school_year = school_year_factory()

    first = ensure_terms(school_year=school_year)
    second = ensure_terms(school_year=school_year)

    token = active_workspace.set(member_membership.workspace_id)
    try:
        numbers = sorted(Term.objects.filter(school_year=school_year).values_list("number", flat=True))
    finally:
        active_workspace.reset(token)

    assert [t.number for t in first] == [1, 2, 3]
    assert [t.number for t in second] == [1, 2, 3]
    assert numbers == [1, 2, 3]


def test_create_activity_rejects_bad_tipo(
    member_membership, group_factory, school_year_factory
):
    from grades.models import Activity
    from grades.services import create_activity, ensure_terms
    from workspaces.context import active_workspace

    school_year = school_year_factory()
    group = group_factory(school_year=school_year)
    terms = ensure_terms(school_year=school_year)

    with pytest.raises(ValidationError):
        create_activity(
            membership=member_membership,
            group=group,
            term=terms[0],
            title="Bad",
            activity_type="homework",
            due_date=datetime.date(2026, 8, 15),
            formative_field_id="languages",
            subject_ids=["spanish"],
        )

    token = active_workspace.set(member_membership.workspace_id)
    try:
        assert Activity.objects.count() == 0
    finally:
        active_workspace.reset(token)


def test_create_activity_rejects_empty_subjects(
    member_membership, group_factory, school_year_factory
):
    from grades.models import Activity
    from grades.services import create_activity, ensure_terms
    from workspaces.context import active_workspace

    school_year = school_year_factory()
    group = group_factory(school_year=school_year)
    terms = ensure_terms(school_year=school_year)

    with pytest.raises(ValidationError):
        create_activity(
            membership=member_membership,
            group=group,
            term=terms[0],
            title="Empty subjects",
            activity_type="task",
            due_date=datetime.date(2026, 8, 15),
            formative_field_id="languages",
            subject_ids=[],
        )

    token = active_workspace.set(member_membership.workspace_id)
    try:
        assert Activity.objects.count() == 0
    finally:
        active_workspace.reset(token)


def test_create_activity_rejects_subject_outside_field(
    member_membership, group_factory, school_year_factory
):
    from grades.models import Activity
    from grades.services import create_activity, ensure_terms
    from workspaces.context import active_workspace

    school_year = school_year_factory()
    group = group_factory(school_year=school_year)
    terms = ensure_terms(school_year=school_year)

    with pytest.raises(ValidationError):
        create_activity(
            membership=member_membership,
            group=group,
            term=terms[0],
            title="Cross field",
            activity_type="task",
            due_date=datetime.date(2026, 8, 15),
            formative_field_id="languages",
            subject_ids=["mathematics"],  # belongs to scientific-thinking
        )

    token = active_workspace.set(member_membership.workspace_id)
    try:
        assert Activity.objects.count() == 0
    finally:
        active_workspace.reset(token)


def test_create_activity_persists_valid_row(
    member_membership, group_factory, school_year_factory
):
    from grades.services import create_activity, ensure_terms

    school_year = school_year_factory()
    group = group_factory(school_year=school_year)
    terms = ensure_terms(school_year=school_year)

    activity = create_activity(
        membership=member_membership,
        group=group,
        term=terms[0],
        title="Ensayo literario",
        activity_type="task",
        due_date=datetime.date(2026, 8, 15),
        formative_field_id="languages",
        subject_ids=["spanish", "english"],
        description="Leer y escribir",
    )

    assert activity.title == "Ensayo literario"
    assert activity.activity_type == "task"
    assert activity.subject_ids == ["spanish", "english"]
    assert activity.workspace_id == member_membership.workspace_id


def test_list_activities_filters_and_stats(
    member_membership, group_factory, school_year_factory, student_factory
):
    from grades.services import (
        bulk_upsert_scores,
        create_activity,
        ensure_terms,
        list_activities,
    )

    school_year = school_year_factory()
    group = group_factory(school_year=school_year)
    terms = ensure_terms(school_year=school_year)
    student = student_factory(group=group)

    task = create_activity(
        membership=member_membership,
        group=group,
        term=terms[0],
        title="Tarea español",
        activity_type="task",
        due_date=datetime.date(2026, 8, 10),
        formative_field_id="languages",
        subject_ids=["spanish"],
    )
    create_activity(
        membership=member_membership,
        group=group,
        term=terms[0],
        title="Examen mates",
        activity_type="exam",
        due_date=datetime.date(2026, 8, 20),
        formative_field_id="scientific-thinking",
        subject_ids=["mathematics"],
    )
    bulk_upsert_scores(
        membership=member_membership,
        group=group,
        entries=[{"student": student, "activity": task, "score": Decimal("8.0")}],
    )

    result = list_activities(
        membership=member_membership,
        group=group,
        term=terms[0],
        field="languages",
    )
    assert len(result["activities"]) == 1
    assert result["activities"][0].title == "Tarea español"
    assert result["stats"]["total_activities"] == 1
    assert result["stats"]["graded_activities"] == 1
    assert result["stats"]["pending_activities"] == 0
    assert result["stats"]["average_score"] == Decimal("8.0")

    by_type = list_activities(
        membership=member_membership,
        group=group,
        term=terms[0],
        type="exam",
    )
    assert len(by_type["activities"]) == 1
    assert by_type["activities"][0].title == "Examen mates"

    by_q = list_activities(
        membership=member_membership,
        group=group,
        term=terms[0],
        q="español",
    )
    assert len(by_q["activities"]) == 1


def test_get_score_matrix_null_not_zero(
    member_membership, group_factory, school_year_factory, student_factory
):
    from grades.services import (
        bulk_upsert_scores,
        create_activity,
        ensure_terms,
        get_score_matrix,
    )

    school_year = school_year_factory()
    group = group_factory(school_year=school_year)
    terms = ensure_terms(school_year=school_year)
    student_a = student_factory(group=group, first_name="Ana")
    student_b = student_factory(group=group, first_name="Beto")
    activity = create_activity(
        membership=member_membership,
        group=group,
        term=terms[0],
        title="Quiz",
        activity_type="activity",
        due_date=datetime.date(2026, 8, 12),
        formative_field_id="languages",
        subject_ids=["spanish"],
    )
    bulk_upsert_scores(
        membership=member_membership,
        group=group,
        entries=[
            {"student": student_a, "activity": activity, "score": Decimal("8.5")},
        ],
    )

    matrix = get_score_matrix(
        membership=member_membership,
        group=group,
        term=terms[0],
    )

    assert len(matrix["students"]) == 2
    assert len(matrix["activities"]) == 1
    by_pair = {
        (row["student_id"], row["activity_id"]): row["score"]
        for row in matrix["scores"]
    }
    assert by_pair[(student_a.pk, activity.pk)] == Decimal("8.5")
    assert by_pair[(student_b.pk, activity.pk)] is None
    assert by_pair[(student_b.pk, activity.pk)] != Decimal("0.0")


def test_bulk_upsert_rejects_score_above_ten_with_no_partial_write(
    member_membership, group_factory, school_year_factory, student_factory
):
    from grades.models import ActivityScore
    from grades.services import bulk_upsert_scores, create_activity, ensure_terms
    from workspaces.context import active_workspace

    school_year = school_year_factory()
    group = group_factory(school_year=school_year)
    terms = ensure_terms(school_year=school_year)
    student = student_factory(group=group)
    activity = create_activity(
        membership=member_membership,
        group=group,
        term=terms[0],
        title="Quiz",
        activity_type="exam",
        due_date=datetime.date(2026, 8, 12),
        formative_field_id="languages",
        subject_ids=["spanish"],
    )

    with pytest.raises(ValidationError):
        bulk_upsert_scores(
            membership=member_membership,
            group=group,
            entries=[
                {"student": student, "activity": activity, "score": Decimal("10.5")},
            ],
        )

    token = active_workspace.set(member_membership.workspace_id)
    try:
        assert ActivityScore.objects.count() == 0
    finally:
        active_workspace.reset(token)


def test_bulk_upsert_wrong_group_student_no_partial_write(
    member_membership, membership_factory, group_factory, school_year_factory, student_factory
):
    from grades.models import ActivityScore
    from grades.services import bulk_upsert_scores, create_activity, ensure_terms
    from workspaces.context import active_workspace

    school_year = school_year_factory()
    group = group_factory(school_year=school_year)
    terms = ensure_terms(school_year=school_year)
    student_in = student_factory(group=group, first_name="Ana")
    other_membership = membership_factory("member")
    other_year = school_year_factory(membership=other_membership)
    other_group = group_factory(membership=other_membership, school_year=other_year)
    outsider = student_factory(
        membership=other_membership, group=other_group, first_name="Carla"
    )
    activity = create_activity(
        membership=member_membership,
        group=group,
        term=terms[0],
        title="Quiz",
        activity_type="task",
        due_date=datetime.date(2026, 8, 12),
        formative_field_id="languages",
        subject_ids=["spanish"],
    )

    with pytest.raises(ValueError):
        bulk_upsert_scores(
            membership=member_membership,
            group=group,
            entries=[
                {"student": student_in, "activity": activity, "score": Decimal("9.0")},
                {"student": outsider, "activity": activity, "score": Decimal("8.0")},
            ],
        )

    token = active_workspace.set(member_membership.workspace_id)
    try:
        assert ActivityScore.objects.count() == 0
    finally:
        active_workspace.reset(token)


def test_bulk_upsert_uses_membership_workspace_only(
    member_membership, membership_factory, group_factory, school_year_factory, student_factory
):
    from grades.models import ActivityScore
    from grades.services import bulk_upsert_scores, create_activity, ensure_terms
    from workspaces.context import active_workspace

    school_year = school_year_factory()
    group = group_factory(school_year=school_year)
    terms = ensure_terms(school_year=school_year)
    student = student_factory(group=group)
    other_membership = membership_factory("member")
    activity = create_activity(
        membership=member_membership,
        group=group,
        term=terms[0],
        title="Quiz",
        activity_type="task",
        due_date=datetime.date(2026, 8, 12),
        formative_field_id="languages",
        subject_ids=["spanish"],
    )

    bulk_upsert_scores(
        membership=member_membership,
        group=group,
        entries=[
            {"student": student, "activity": activity, "score": Decimal("7.5")},
        ],
    )

    token = active_workspace.set(member_membership.workspace_id)
    try:
        score = ActivityScore.objects.get(student=student, activity=activity)
    finally:
        active_workspace.reset(token)

    assert score.workspace_id == member_membership.workspace_id
    assert score.workspace_id != other_membership.workspace_id
    assert score.score == Decimal("7.5")
