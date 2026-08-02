"""Services layer for Term / Activity / ActivityScore (grades spec)."""

from __future__ import annotations

import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Avg, Count, QuerySet

from grades.models import Activity, ActivityScore, Term
from lesson_plans.core import catalog
from schools.models import Group, SchoolYear
from students.models import Student
from workspaces.scope import workspace_scope


def _validate_group_workspace(*, membership, group: Group) -> None:
    if group.workspace_id != membership.workspace_id:
        raise ValueError("Group does not belong to the caller's workspace.")


def ensure_terms(*, school_year: SchoolYear) -> list[Term]:
    """Idempotently seed Terms 1–3 for `school_year`."""
    with workspace_scope(school_year.workspace_id):
        existing = {
            term.number: term
            for term in Term.objects.filter(school_year=school_year)
        }
        created: list[Term] = []
        for number in (1, 2, 3):
            term = existing.get(number)
            if term is None:
                term = Term(
                    workspace=school_year.workspace,
                    school_year=school_year,
                    number=number,
                )
                term.full_clean()
                term.save()
            created.append(term)
        return sorted(created, key=lambda t: t.number)


def _validate_catalog(*, formative_field_id: str, subject_ids: list[str]) -> None:
    if not subject_ids:
        raise ValidationError({"subject_ids": "At least one subject is required."})
    try:
        catalog.field_by_id(formative_field_id)
    except KeyError as exc:
        raise ValidationError({"formative_field_id": str(exc)}) from exc
    for subject_id in subject_ids:
        try:
            catalog.subject_by_id(formative_field_id, subject_id)
        except KeyError as exc:
            raise ValidationError({"subject_ids": str(exc)}) from exc


def create_activity(
    *,
    membership,
    group: Group,
    term: Term,
    title: str,
    activity_type: str,
    due_date: datetime.date,
    formative_field_id: str,
    subject_ids: list[str],
    description: str = "",
) -> Activity:
    """Create an Activity after catalog + tipo validation. Workspace from membership."""
    _validate_group_workspace(membership=membership, group=group)
    if group.workspace_id != term.workspace_id:
        raise ValueError("Term does not belong to the caller's workspace.")
    if activity_type not in set(Activity.ActivityType.values):
        raise ValidationError({"activity_type": f"Invalid activity_type: {activity_type!r}"})
    _validate_catalog(
        formative_field_id=formative_field_id, subject_ids=subject_ids
    )

    with workspace_scope(membership.workspace_id):
        activity = Activity(
            workspace=membership.workspace,
            group=group,
            term=term,
            title=title,
            activity_type=activity_type,
            due_date=due_date,
            formative_field_id=formative_field_id,
            subject_ids=list(subject_ids),
            description=description or "",
        )
        activity.full_clean()
        activity.save()
        return activity


def _filter_activities(
    qs: QuerySet[Activity],
    *,
    field: str | None,
    subject: str | None,
    type: str | None,
    q: str | None,
) -> QuerySet[Activity]:
    if field:
        qs = qs.filter(formative_field_id=field)
    if subject:
        qs = qs.filter(subject_ids__contains=[subject])
    if type:
        qs = qs.filter(activity_type=type)
    if q:
        qs = qs.filter(title__icontains=q)
    return qs


def _compute_stats(
    *, activities: list[Activity], student_count: int
) -> dict[str, int | Decimal | None]:
    if not activities:
        return {
            "total_activities": 0,
            "graded_activities": 0,
            "pending_activities": 0,
            "average_score": None,
        }

    activity_ids = [a.pk for a in activities]
    score_rows = (
        ActivityScore.objects.filter(activity_id__in=activity_ids)
        .exclude(score__isnull=True)
        .values("activity_id")
        .annotate(scored=Count("id"), avg=Avg("score"))
    )
    scored_by_activity = {row["activity_id"]: row for row in score_rows}

    graded = 0
    for activity in activities:
        row = scored_by_activity.get(activity.pk)
        if row is not None and student_count > 0 and row["scored"] >= student_count:
            graded += 1

    averages = [
        row["avg"]
        for row in scored_by_activity.values()
        if row["avg"] is not None
    ]
    average_score = None
    if averages:
        average_score = (
            Decimal(str(sum(averages) / len(averages))).quantize(Decimal("0.1"))
        )

    total = len(activities)
    return {
        "total_activities": total,
        "graded_activities": graded,
        "pending_activities": total - graded,
        "average_score": average_score,
    }


def list_activities(
    *,
    membership,
    group: Group,
    term: Term,
    field: str | None = None,
    subject: str | None = None,
    type: str | None = None,
    q: str | None = None,
) -> dict:
    """Return filtered activities plus aggregate stats for the group/term."""
    _validate_group_workspace(membership=membership, group=group)

    with workspace_scope(membership.workspace_id):
        qs = Activity.objects.filter(group=group, term=term)
        qs = _filter_activities(qs, field=field, subject=subject, type=type, q=q)
        activities = list(qs.order_by("due_date", "pk"))
        student_count = Student.objects.filter(group=group).count()
        stats = _compute_stats(activities=activities, student_count=student_count)
        return {"activities": activities, "stats": stats}


def get_score_matrix(
    *,
    membership,
    group: Group,
    term: Term,
    field: str | None = None,
    subject: str | None = None,
    type: str | None = None,
) -> dict:
    """Students × activities with scores; missing rows surface as null (not 0.0)."""
    _validate_group_workspace(membership=membership, group=group)

    with workspace_scope(membership.workspace_id):
        students = list(
            Student.objects.filter(group=group).order_by(
                "last_name_paternal", "first_name"
            )
        )
        qs = Activity.objects.filter(group=group, term=term)
        qs = _filter_activities(qs, field=field, subject=subject, type=type, q=None)
        activities = list(qs.order_by("due_date", "pk"))

        existing = {
            (score.student_id, score.activity_id): score.score
            for score in ActivityScore.objects.filter(
                activity__in=activities, student__in=students
            )
        }

        scores: list[dict] = []
        for student in students:
            for activity in activities:
                scores.append(
                    {
                        "student_id": student.pk,
                        "activity_id": activity.pk,
                        "score": existing.get((student.pk, activity.pk)),
                    }
                )

        return {
            "students": students,
            "activities": activities,
            "scores": scores,
        }


def bulk_upsert_scores(*, membership, group: Group, entries: list[dict]) -> None:
    """Atomically upsert ActivityScore rows. Workspace always from membership."""
    _validate_group_workspace(membership=membership, group=group)

    with workspace_scope(membership.workspace_id):
        group_student_ids = set(
            Student.objects.filter(group=group).values_list("pk", flat=True)
        )
        activity_ids = {entry["activity"].pk for entry in entries}
        group_activity_ids = set(
            Activity.objects.filter(group=group, pk__in=activity_ids).values_list(
                "pk", flat=True
            )
        )

        validated: list[ActivityScore] = []
        for entry in entries:
            student = entry["student"]
            activity = entry["activity"]
            score = entry.get("score")

            if student.pk not in group_student_ids:
                raise ValueError("Student does not belong to the supplied group.")
            if student.workspace_id != membership.workspace_id:
                raise ValueError("Student does not belong to the caller's workspace.")
            if activity.pk not in group_activity_ids:
                raise ValueError("Activity does not belong to the supplied group.")
            if activity.workspace_id != membership.workspace_id:
                raise ValueError("Activity does not belong to the caller's workspace.")

            record = ActivityScore(
                workspace=membership.workspace,
                activity=activity,
                student=student,
                score=score,
            )
            record.full_clean()
            validated.append(record)

        with transaction.atomic():
            for record in validated:
                ActivityScore.objects.update_or_create(
                    activity=record.activity,
                    student=record.student,
                    defaults={
                        "workspace": membership.workspace,
                        "score": record.score,
                    },
                )
