"""Teacher-minimal persona — one school, one ciclo, one grupo.

The simplest usable demo: a teacher who just registered and set up their
first classroom. No students, no lesson plans — enough to navigate the
UI and see the structure.
"""

from __future__ import annotations

from schools.models import School
from schools.services import create_group, create_school, create_school_year
from workspaces.models import Membership

from .base import DemoProvisioner


class TeacherMinimal(DemoProvisioner):
    """Provisioner for the ``teacher_minimal`` demo persona."""

    persona_key = "teacher_minimal"

    def seed(self, *, membership: Membership) -> None:
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
        create_group(
            membership=membership,
            school_year=school_year,
            grado=1,
            grupo="A",
        )