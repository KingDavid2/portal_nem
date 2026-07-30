"""Tests for the showcase provisioning persona (P6 Slice 4).

Showcase seeds one school + ciclo + ``1°A`` + 10 students via services, then
two ready ``LessonPlan`` rows written directly (TeacherFull's documented
exception) so the demo can render grounding ✓/⚠ and P1 provenance without
an LLM call. ``cost_micros`` / ``duration_ms`` stay soft-deferred (no P3
columns).
"""

from __future__ import annotations

import pytest

from demo.provisioning.showcase import Showcase
from lesson_plans.core.catalog import content_by_id, pda_by_id
from lesson_plans.models import GenerationUsage, LessonPlan
from schools.models import Group, School, SchoolYear
from students.models import Student
from workspaces.scope import workspace_scope

pytestmark = pytest.mark.django_db

_CLEAN_TITLE = "Conociendo y protegiendo el ecosistema de nuestra comunidad"
_WARNING_TITLE = "Relatos de nuestra comunidad"
_OFFENDING_PDA = pda_by_id("languages", "languages-coherent-texts").text
_SELECTED_PDA = pda_by_id("languages", "languages-accentuation").text
_LANGUAGES_CONTENT = content_by_id("languages", "languages-text-resources").text


class TestShowcaseShape:
    """School / ciclo / grupo / students match the showcase seed shape."""

    def test_seeds_one_school_one_ciclo_one_grupo(self) -> None:
        _, workspace = Showcase().provision()

        with workspace_scope(workspace.id):
            assert School.objects.count() == 1
            assert SchoolYear.objects.count() == 1
            assert Group.objects.count() == 1
            group = Group.objects.get()
            assert group.grado == 1
            assert group.grupo == "A"

    def test_seeds_exactly_ten_students_in_grupo_a(self) -> None:
        _, workspace = Showcase().provision()

        with workspace_scope(workspace.id):
            assert Student.objects.count() == 10
            group = Group.objects.get()
            assert Student.objects.filter(group=group).count() == 10


class TestShowcasePlans:
    """Two ready plans: clean grounding ✓ and warning grounding ⚠."""

    def test_seeds_two_ready_plans_with_distinct_titles(self) -> None:
        _, workspace = Showcase().provision()

        with workspace_scope(workspace.id):
            plans = list(LessonPlan.objects.order_by("title"))
            assert len(plans) == 2
            titles = {plan.title for plan in plans}
            assert titles == {_CLEAN_TITLE, _WARNING_TITLE}
            for plan in plans:
                assert plan.status == LessonPlan.Status.READY
                assert plan.proyecto is not None
                assert plan.group_id is not None

    def test_clean_plan_shows_grounding_check_with_provenance(self) -> None:
        """Clean plan: invented_pdas=False (✓) + P1 provenance fields present."""
        _, workspace = Showcase().provision()

        with workspace_scope(workspace.id):
            plan = LessonPlan.objects.get(title=_CLEAN_TITLE)
            assert plan.invented_pdas is False
            assert plan.invented_pda_texts == []
            assert plan.grounding_selections
            assert isinstance(plan.grounding_selections, list)
            assert plan.grounding_selections[0]["content"]
            assert plan.grounding_selections[0]["pdas"]
            assert plan.provider == "anthropic"
            assert plan.model_name
            assert plan.prompt_tokens is not None
            assert plan.completion_tokens is not None
            assert plan.generated_at is not None

    def test_warning_plan_flags_off_selection_pda(self) -> None:
        """Warning plan: languages-accentuation selected; coherent-texts invented."""
        _, workspace = Showcase().provision()

        with workspace_scope(workspace.id):
            plan = LessonPlan.objects.get(title=_WARNING_TITLE)
            assert plan.invented_pdas is True
            assert plan.invented_pda_texts == [_OFFENDING_PDA]
            assert plan.grounding_selections == [
                {
                    "content": _LANGUAGES_CONTENT,
                    "pdas": [_SELECTED_PDA],
                }
            ]
            assert plan.provider == "anthropic"
            assert plan.model_name
            assert plan.prompt_tokens is not None
            assert plan.completion_tokens is not None
            assert plan.generated_at is not None

    def test_zero_generation_usage_rows(self) -> None:
        """No LLM path ran — the generation ledger must stay empty."""
        _, workspace = Showcase().provision()

        with workspace_scope(workspace.id):
            assert GenerationUsage.objects.count() == 0

    def test_cost_and_duration_soft_deferred(self) -> None:
        """P3 columns are absent; seed must not invent them."""
        _, workspace = Showcase().provision()

        with workspace_scope(workspace.id):
            for plan in LessonPlan.objects.all():
                assert not hasattr(plan, "cost_micros")
                assert not hasattr(plan, "duration_ms")
                # Soft-defer contract: if attrs ever appear, they stay null.
                cost = getattr(plan, "cost_micros", None)
                duration = getattr(plan, "duration_ms", None)
                assert cost is None
                assert duration is None
