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

    class Scenario(models.TextChoices):
        """Scope the proyecto acts on. Stored values are stable ids; the
        frontend renders them as "Aula" / "Escuela" / "Comunidad"."""

        CLASSROOM = "classroom", "Classroom"
        SCHOOL = "school", "School"
        COMMUNITY = "community", "Community"

    group = models.ForeignKey(
        "schools.Group", on_delete=models.PROTECT, related_name="lesson_plans"
    )
    campo = models.CharField(max_length=200)
    grade = models.CharField(max_length=50)
    theme = models.TextField()
    # Project context captured by the planning form. Every column is nullable
    # or defaulted so existing rows stay valid; the id columns hold catalog
    # ids (`lesson_plans.core.catalog`) that a later unit validates at the
    # write boundary — this model only stores them.
    field_id = models.CharField(max_length=50, blank=True)
    subject_id = models.CharField(max_length=50, blank=True)
    methodology_id = models.CharField(max_length=50, blank=True)
    duration_weeks = models.PositiveSmallIntegerField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    scenario = models.CharField(max_length=20, choices=Scenario.choices, blank=True)
    context_diagnosis = models.TextField(blank=True)
    # `[str]` — cross-cutting theme (`eje articulador`) catalog ids.
    cross_cutting_theme_ids = models.JSONField(default=list, blank=True)
    # `[{"content_id": str, "pda_ids": [str, ...]}]` — official contents and
    # the PDAs selected under each one, by catalog id.
    content_selections = models.JSONField(default=list, blank=True)
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
    # The verbatim PDAs the fidelity guard flagged as invented, so the audit
    # trail shows exactly what was checked and what did not match — not just
    # that something was wrong.
    invented_pda_texts = models.JSONField(default=list, blank=True)
    # A snapshot of the verbatim official text this plan was checked against,
    # not the catalog ids from `content_selections`. The viewer must faithfully
    # render what the plan was grounded on at generation time, even if the
    # underlying catalog entry has since been edited or retired; re-resolving
    # from ids at read time would silently rewrite the audit trail.
    grounding_selections = models.JSONField(default=list, blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "lesson_plans_lessonplan"

    def __str__(self) -> str:
        return f"{self.group_id}:{self.theme}:{self.status}"


class GenerationUsage(ScopedModel):
    """Append-only per-workspace ledger of accepted generations in one month.

    Deliberately NOT derived from `LessonPlan.objects.filter(...).count()`: a
    derived counter would refund quota whenever a plan is deleted, making the
    monthly limit farmable by create-then-delete. One row per
    (workspace, period); `count` only ever moves forward within a period.

    `period` is the first day of the month the generations were consumed in
    (see `lesson_plans.quota` for the window semantics).
    """

    period = models.DateField()
    count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "lesson_plans_generationusage"
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "period"],
                name="unique_workspace_generation_period",
            )
        ]

    def __str__(self) -> str:
        return f"{self.workspace_id}:{self.period:%Y-%m}:{self.count}"
