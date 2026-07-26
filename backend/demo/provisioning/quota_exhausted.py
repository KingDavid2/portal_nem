"""Quota-exhausted persona — everything from teacher_full plus a maxed-out generation quota.

Extends ``TeacherFull`` so the workspace is fully seeded with school,
grupos, students and ready lesson plans — then writes a single
``GenerationUsage`` row at the monthly limit so the 429 quota path is
demoable immediately without looping ``consume_generation``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lesson_plans.models import GenerationUsage
from lesson_plans.quota import current_period, monthly_limit

from .base import DemoProvisioner
from .teacher_full import TeacherFull

if TYPE_CHECKING:
    from workspaces.models import Membership


class QuotaExhausted(TeacherFull):
    """Provisioner for the ``quota_exhausted`` demo persona.

    Inherits all seeding from ``TeacherFull`` (school, ciclo, 2 grupos,
    20 students, 2 ready plans) and then creates one ``GenerationUsage``
    row keyed to the current period with ``count = monthly_limit()``, so
    ``current_usage(workspace)`` reports the workspace as fully used.
    """

    persona_key = "quota_exhausted"

    def seed(self, *, membership: Membership) -> None:
        # Seed everything the teacher_full persona provides.
        super().seed(membership=membership)

        # Mark the workspace quota as fully consumed in one atomic write.
        # This avoids looping consume_generation 30 times (which would be
        # slower and fragile if the setting ever changes).
        GenerationUsage.objects.create(
            workspace=membership.workspace,
            period=current_period(),
            count=monthly_limit(),
        )