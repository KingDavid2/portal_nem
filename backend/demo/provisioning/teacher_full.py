"""Teacher-full persona — school, ciclo, two grupos, ~20 students, two ready lesson plans.

The richest demo profile: a teacher who has already set up two classes
and generated two lesson plans, so the evaluator can browse the UI end
to end (plan list, plan detail, project rendering).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from django.utils import timezone

from lesson_plans.core.catalog import COMMUNITY_BASED_PROJECT_LEARNING, field_by_id
from lesson_plans.models import LessonPlan
from schools.models import School
from schools.services import create_group, create_school, create_school_year
from students.services import create_student

from .base import DemoProvisioner

if TYPE_CHECKING:
    from workspaces.models import Membership

# 20 realistic Mexican student names — each triple is (first_name, paternal, maternal).
# Stored as a module-level tuple to keep the seed body compact and readable.
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
    ("Valeria", "Flores", "Díaz"),
    ("Daniel", "Torres", "Morales"),
    ("Camila", "Díaz", "Reyes"),
    ("Alejandro", "Morales", "Ortiz"),
    ("Victoria", "Reyes", "Jiménez"),
    ("Samuel", "Ortiz", "Ramos"),
    ("Fernanda", "Jiménez", "Vargas"),
    ("Abel", "Ramos", "Castillo"),
    ("Ximena", "Vargas", "Mendoza"),
    ("Gabriel", "Castillo", "Romero"),
)

# Pre-generated proyectos, one per seeded plan. They were produced by the real
# LLM pipeline and match the ``Proyecto`` Pydantic model in
# ``lesson_plans/core/schema.py``, so the demo renders exactly like a real plan.
_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

# The two seeded plans: (grupo, fixture file, field id, subject id, theme). The
# catalog ids come from `lesson_plans.core.catalog` — hardcoding the display
# label instead would drift the moment the catalog is renamed.
_SEEDED_PLANS: tuple[tuple[str, str, str, str, str], ...] = (
    (
        "A",
        "proyecto_demo.json",
        "ethics-nature-societies",
        "geography",
        "Conociendo y protegiendo el ecosistema de nuestra comunidad",
    ),
    (
        "B",
        "proyecto_lenguajes.json",
        "languages",
        "spanish",
        "Narrativas de nuestra comunidad: relatos y memorias orales",
    ),
)


def _load_proyecto_fixture(name: str) -> dict:
    """Load a pre-generated proyecto payload from disk."""
    with open(_FIXTURES_DIR / name, encoding="utf-8") as handle:
        return json.load(handle)


class TeacherFull(DemoProvisioner):
    """Provisioner for the ``teacher_full`` demo persona.

    Seeds:
    - one school + one ciclo (same Mexican secundaria as teacher_minimal)
    - two grupos (1°A, 1°B)
    - 20 students spread evenly across the two grupos
    - two ``LessonPlan`` rows in ``status = ready``, written directly
      because the real creation path would call the LLM (demo exception)
    """

    persona_key = "teacher_full"

    def seed(self, *, membership: Membership) -> None:
        workspace = membership.workspace

        # --- School & ciclo ---------------------------------------------------
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

        # --- Two grupos --------------------------------------------------------
        grupo_a = create_group(
            membership=membership,
            school_year=school_year,
            grado=1,
            grupo="A",
        )
        grupo_b = create_group(
            membership=membership,
            school_year=school_year,
            grado=1,
            grupo="B",
        )

        # --- 20 students across both grupos ------------------------------------
        for i, (first_name, paternal, maternal) in enumerate(_STUDENT_NAMES):
            create_student(
                membership=membership,
                group=grupo_a if i < 10 else grupo_b,
                first_name=first_name,
                last_name_paternal=paternal,
                last_name_maternal=maternal,
            )

        # --- Two ready LessonPlans ---------------------------------------------
        # Bypass the services layer here: the real create path triggers the LLM,
        # which is precisely what the demo user is invited to try themselves.
        # Seeding pre-generated proyectos instead lets the evaluator browse a
        # populated plan list from the first second. The catalog ids are the same
        # ones `lesson_plans.services` writes, so the UI resolves them normally.
        for group, fixture_name, field_id, subject_id, theme in _SEEDED_PLANS:
            proyecto = _load_proyecto_fixture(fixture_name)
            LessonPlan.objects.create(
                workspace=workspace,
                group=grupo_a if group == "A" else grupo_b,
                campo=field_by_id(field_id).name,
                grade="1º",
                theme=theme,
                title=proyecto["title"],
                proyecto=proyecto,
                field_id=field_id,
                subject_id=subject_id,
                methodology_id=COMMUNITY_BASED_PROJECT_LEARNING.id,
                status=LessonPlan.Status.READY,
                generated_at=timezone.now(),
            )
