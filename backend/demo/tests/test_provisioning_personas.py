"""Tests for the teacher_full and quota_exhausted provisioning personas.

Validates that ``TeacherFull`` seeds the full workspace (school, ciclo,
two grupos with students distributed across both, two ready lesson plans)
and that ``QuotaExhausted`` inherits all of that plus a maxed-out generation
quota. Every assertion is scoped through ``workspace_scope`` so RLS
applies the same way it would in production.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from demo.provisioning.quota_exhausted import QuotaExhausted
from demo.provisioning.teacher_full import TeacherFull
from lesson_plans.core.catalog import FIELDS, field_by_id
from lesson_plans.core.schema import Proyecto
from lesson_plans.models import GenerationUsage, LessonPlan
from lesson_plans.quota import current_period, current_usage, monthly_limit
from schools.models import Group, School, SchoolYear
from students.models import Student
from workspaces.scope import workspace_scope

pytestmark = pytest.mark.django_db

# Fixtures live alongside the provisioning module — loaded from disk so the
# tests validate the same JSON the provisioner reads at runtime.
_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
_FIXTURE_NAMES = ("proyecto_demo.json", "proyecto_lenguajes.json")


def _load(name: str) -> dict:
    with open(_FIXTURES_DIR / name, encoding="utf-8") as handle:
        return json.load(handle)


class TestTeacherFull:
    """``TeacherFull`` provisions the complete demo workspace."""

    def test_seeds_one_school(self) -> None:
        user, workspace = TeacherFull().provision()

        with workspace_scope(workspace.id):
            assert School.objects.count() == 1
            school = School.objects.first()
            assert school.workspace_id == workspace.id
            assert school.level == School.Level.SECUNDARIA

    def test_seeds_one_ciclo(self) -> None:
        _, workspace = TeacherFull().provision()

        with workspace_scope(workspace.id):
            school = School.objects.first()
            assert SchoolYear.objects.filter(school=school).count() == 1

    def test_seeds_exactly_two_grupos(self) -> None:
        _, workspace = TeacherFull().provision()

        with workspace_scope(workspace.id):
            assert Group.objects.count() == 2

    def test_students_distributed_across_both_grupos(self) -> None:
        """All 20 students are seeded and each grupo has at least one.

        A test that only checks the total count would pass if all 20
        landed in one grupo — this one asserts per-grupo distribution.
        """
        _, workspace = TeacherFull().provision()

        with workspace_scope(workspace.id):
            total = Student.objects.count()
            assert total == 20

            grupos = Group.objects.all()
            for group in grupos:
                count = Student.objects.filter(group=group).count()
                assert count >= 1, (
                    f"Group {group} has zero students — all {total} "
                    "may have landed in the other grupo."
                )

    def test_seeds_two_ready_lesson_plans(self) -> None:
        """TeacherFull creates exactly 2 lesson plans, both in ready status,
        both with a non-empty proyecto payload, scoped to the workspace.
        """
        _, workspace = TeacherFull().provision()

        with workspace_scope(workspace.id):
            plans = LessonPlan.objects.all()
            assert plans.count() == 2

            for plan in plans:
                assert plan.status == LessonPlan.Status.READY
                assert plan.proyecto is not None, "proyecto must be a dict, not None"
                assert isinstance(plan.proyecto, dict)
                assert plan.proyecto.get("title"), "proyecto.title must be non-empty"
                assert plan.workspace_id == workspace.id
                assert plan.group_id is not None

    def test_plans_carry_resolvable_catalog_ids(self) -> None:
        """`campo` must be the label of the plan's own `field_id`.

        The list and detail screens read `field_id`/`subject_id` to resolve
        catalog labels; a plan seeded with only the display string would
        render with an empty campo selector.
        """
        _, workspace = TeacherFull().provision()

        with workspace_scope(workspace.id):
            for plan in LessonPlan.objects.all():
                assert plan.field_id, "plan must carry a catalog field_id"
                assert plan.subject_id
                assert plan.methodology_id
                assert plan.campo == field_by_id(plan.field_id).name

    def test_the_two_plans_use_different_proyectos(self) -> None:
        """Both plans loading the same fixture would make the demo look broken."""
        _, workspace = TeacherFull().provision()

        with workspace_scope(workspace.id):
            titles = {plan.title for plan in LessonPlan.objects.all()}
            assert len(titles) == 2

    def test_plan_groups_are_seeded_grupos(self) -> None:
        """Each lesson plan is attached to a grupo that was seeded."""
        _, workspace = TeacherFull().provision()

        with workspace_scope(workspace.id):
            plans = LessonPlan.objects.all()
            plan_group_ids = {plan.group_id for plan in plans}
            seeded_group_ids = {g.id for g in Group.objects.all()}
            assert plan_group_ids.issubset(seeded_group_ids)


class TestProyectoFixture:
    """The JSON fixtures match the ``Proyecto`` Pydantic schema shape.

    Every seeded fixture is checked, not just the first one — a malformed
    second fixture would otherwise ship a blank plan detail page.
    """

    @pytest.mark.parametrize("name", _FIXTURE_NAMES)
    def test_fixture_validates_against_the_real_schema(self, name: str) -> None:
        """The fixture must round-trip through the same Pydantic model the
        generation pipeline validates LLM output with — that is the only
        check that stays true when the schema changes."""
        Proyecto.model_validate(_load(name))

    @pytest.mark.parametrize("name", _FIXTURE_NAMES)
    def test_fixture_has_required_top_level_keys(self, name: str) -> None:
        """Assert on the actual keys the app reads, not just 'is not None'."""
        required_keys = {
            "datos",
            "title",
            "purpose",
            "articulating_axes",
            "problem_or_theme",
            "contents_and_pdas",
            "stages",
            "rubric",
        }
        assert required_keys.issubset(_load(name).keys())

    @pytest.mark.parametrize("name", _FIXTURE_NAMES)
    def test_fixture_datos_has_required_fields(self, name: str) -> None:
        """The datos block must have the fields the renderers expect."""
        datos_keys = {"school_name", "grade", "campo_formativo", "date"}
        proyecto = _load(name)
        assert datos_keys.issubset(proyecto["datos"].keys())
        assert proyecto["datos"]["phase"] == 6

    @pytest.mark.parametrize("name", _FIXTURE_NAMES)
    def test_fixture_campo_formativo_is_a_real_catalog_label(self, name: str) -> None:
        """A campo the catalog does not know renders as an unmatched label."""
        labels = {field.name for field in FIELDS}
        assert _load(name)["datos"]["campo_formativo"] in labels

    @pytest.mark.parametrize("name", _FIXTURE_NAMES)
    def test_fixture_stages_and_rubric(self, name: str) -> None:
        """Each stage has momentos, each rubric criterion has 4 levels."""
        proyecto = _load(name)
        stages = proyecto["stages"]
        assert len(stages) >= 2
        for stage in stages:
            assert "name" in stage
            assert len(stage["momentos"]) >= 1
            for momento in stage["momentos"]:
                assert "number" in momento
                assert "sessions" in momento
                assert len(momento["sessions"]) >= 1

        rubric = proyecto["rubric"]
        assert len(rubric["criteria"]) >= 1
        for criterion in rubric["criteria"]:
            assert criterion["criterion"]
            assert len(criterion["levels"]) == 4


class TestQuotaExhausted:
    """``QuotaExhausted`` inherits teacher_full data and maxes the quota."""

    def test_inherits_teacher_full_seeds(self) -> None:
        """QuotaExhausted seeds everything TeacherFull does: 1 school, 2 grupos."""
        _, workspace = QuotaExhausted().provision()

        with workspace_scope(workspace.id):
            assert School.objects.count() == 1
            assert Group.objects.count() == 2

    def test_leaves_workspace_at_monthly_limit(self) -> None:
        """current_usage() reports the workspace as fully consumed.

        Asserts against the real quota read path (not a raw row count)
        to ensure the ledger integration is correct.
        """
        _, workspace = QuotaExhausted().provision()

        used, limit = current_usage(workspace)
        assert used == limit, f"Expected {limit} used, got {used}"
        assert limit == monthly_limit()

    def test_generation_usage_row_exists(self) -> None:
        """A GenerationUsage row is actually persisted for the current period."""
        _, workspace = QuotaExhausted().provision()

        with workspace_scope(workspace.id):
            usage = GenerationUsage.objects.filter(
                workspace=workspace, period=current_period()
            ).first()
            assert usage is not None
            assert usage.count == monthly_limit()