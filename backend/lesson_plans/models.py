from django.db import models

from workspaces.models import ScopedModel


class LessonPlan(ScopedModel):
    """An AI-generated NEM ABPC proyecto for a Group (design D3, Interfaces —
    `LessonPlan (ScopedModel)`).

    `group` is `PROTECT` (mirrors `Student.group`) — a generated plan must not
    be silently destroyed by deleting its parent Group. `workspace` (from
    `ScopedModel`) is its own denormalized FK, never derived by joining
    through `group` (tenancy-isolation spec). The service layer (D5) enforces
    the `workspace == group.workspace` invariant — it is deliberately not an
    RLS/DB constraint (design Interfaces/Contracts).
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    group = models.ForeignKey(
        "schools.Group", on_delete=models.PROTECT, related_name="lesson_plans"
    )
    campo = models.CharField(max_length=200)
    grade = models.CharField(max_length=50)
    theme = models.TextField()
    title = models.CharField(max_length=200, blank=True)
    proyecto = models.JSONField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    failure_reason = models.TextField(blank=True)
    provider = models.CharField(max_length=50, blank=True)
    model_name = models.CharField(max_length=100, blank=True)
    prompt_tokens = models.IntegerField(null=True, blank=True)
    completion_tokens = models.IntegerField(null=True, blank=True)
    invented_pdas = models.BooleanField(default=False)
    generated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "lesson_plans_lessonplan"

    def __str__(self) -> str:
        return f"{self.group_id}:{self.theme}:{self.status}"
