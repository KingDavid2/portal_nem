"""Showcase persona — grounding ✓/⚠ + P1 provenance without LLM calls.

One school, one ciclo, one grupo ``1°A``, ten students (via services), then
two ready ``LessonPlan`` rows written directly from the existing demo
fixtures — ``TeacherFull``'s documented exception so the evaluator sees
provenance and grounding markers without burning a generation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from django.utils import timezone

from lesson_plans.core.catalog import (
    COMMUNITY_BASED_PROJECT_LEARNING,
    content_by_id,
    field_by_id,
    pda_by_id,
)
from lesson_plans.models import LessonPlan
from schools.models import School
from schools.services import create_group, create_school, create_school_year
from students.services import create_student

from .base import DemoProvisioner

if TYPE_CHECKING:
    from workspaces.models import Membership

_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

# Ten students for the single showcase grupo (first half of TeacherFull's list).
_STUDENT_NAMES: tuple[tuple[str, str, str], ...] = (
    ("Sofía", "Hernández", "López"),
    ("Mateo", "García", "Martínez"),
    ("Valentina", "Rodríguez", "González"),
    ("Sebastián", "López", "Hernández"),
    ("Isabella", "Martínez", "Pérez"),
    ("Santiago", "González", "Sánchez"),
    ("Renata", "Pérez", "Ramírez"),
    ("Emiliano", "Sánchez", "Cruz"),
    ("Regina", "Ramírez", "Flores"),
    ("Nicolás", "Cruz", "Torres"),
)

# P1 provenance stamped on both seeded plans (no live LLM call).
_PROVIDER = "anthropic"
_MODEL_NAME = "claude-sonnet-4-20250514"
_PROMPT_TOKENS = 1200
_COMPLETION_TOKENS = 800

# Warning recipe: select languages-accentuation only; coherent-texts is invented.
_SELECTED_PDA_ID = "languages-accentuation"
_OFFENDING_PDA_ID = "languages-coherent-texts"
_LANGUAGES_CONTENT_ID = "languages-text-resources"


def _load_proyecto_fixture(name: str) -> dict:
    with open(_FIXTURES_DIR / name, encoding="utf-8") as handle:
        return json.load(handle)


def _warning_grounding() -> tuple[list[dict], list[str]]:
    """Return (grounding_selections, invented_pda_texts) for the ⚠ plan."""
    content = content_by_id("languages", _LANGUAGES_CONTENT_ID)
    selected = pda_by_id("languages", _SELECTED_PDA_ID).text
    invented = pda_by_id("languages", _OFFENDING_PDA_ID).text
    return (
        [{"content": content.text, "pdas": [selected]}],
        [invented],
    )


class Showcase(DemoProvisioner):
    """Provisioner for the ``showcase`` demo persona.

    Seeds:
    - one school + one ciclo + one grupo (1°A) + 10 students via services
    - two ``LessonPlan`` rows in ``status = ready``, written directly:
      clean (proyecto_demo.json, grounding ✓) and warning
      (proyecto_lenguajes.json, grounding ⚠ with off-selection PDA)
    """

    persona_key = "showcase"

    def seed(self, *, membership: Membership) -> None:
        workspace = membership.workspace

        school = create_school(
            membership=membership,
            name="Secundaria General No. 12",
            level=School.Level.SECUNDARIA,
        )
        school_year = create_school_year(
            membership=membership,
            school=school,
            label="2025-2026",
        )
        grupo = create_group(
            membership=membership,
            school_year=school_year,
            grado=1,
            grupo="A",
        )

        for first_name, paternal, maternal in _STUDENT_NAMES:
            create_student(
                membership=membership,
                group=grupo,
                first_name=first_name,
                last_name_paternal=paternal,
                last_name_maternal=maternal,
            )

        # Bypass services: the real create path triggers the LLM. Showcase
        # must render grounding + provenance with zero GenerationUsage rows.
        now = timezone.now()
        clean = _load_proyecto_fixture("proyecto_demo.json")
        LessonPlan.objects.create(
            workspace=workspace,
            group=grupo,
            campo=field_by_id("ethics-nature-societies").name,
            grade="1º",
            theme="Conociendo y protegiendo el ecosistema de nuestra comunidad",
            title=clean["title"],
            proyecto=clean,
            field_id="ethics-nature-societies",
            subject_id="geography",
            methodology_id=COMMUNITY_BASED_PROJECT_LEARNING.id,
            status=LessonPlan.Status.READY,
            provider=_PROVIDER,
            model_name=_MODEL_NAME,
            prompt_tokens=_PROMPT_TOKENS,
            completion_tokens=_COMPLETION_TOKENS,
            invented_pdas=False,
            invented_pda_texts=[],
            grounding_selections=[
                {"content": block["content"], "pdas": list(block["pdas"])}
                for block in clean["contents_and_pdas"]
            ],
            generated_at=now,
        )

        warning = _load_proyecto_fixture("proyecto_lenguajes.json")
        grounding_selections, invented_pda_texts = _warning_grounding()
        LessonPlan.objects.create(
            workspace=workspace,
            group=grupo,
            campo=field_by_id("languages").name,
            grade="1º",
            theme="Narrativas de nuestra comunidad: relatos y memorias orales",
            title=warning["title"],
            proyecto=warning,
            field_id="languages",
            subject_id="spanish",
            methodology_id=COMMUNITY_BASED_PROJECT_LEARNING.id,
            status=LessonPlan.Status.READY,
            provider=_PROVIDER,
            model_name=_MODEL_NAME,
            prompt_tokens=_PROMPT_TOKENS,
            completion_tokens=_COMPLETION_TOKENS,
            invented_pdas=True,
            invented_pda_texts=invented_pda_texts,
            grounding_selections=grounding_selections,
            generated_at=now,
        )
