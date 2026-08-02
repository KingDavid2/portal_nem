from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from workspaces.models import ScopedModel


class Term(ScopedModel):
    """School-year period 1–3 (grades spec — Term Invariants and ensure_terms)."""

    school_year = models.ForeignKey(
        "schools.SchoolYear",
        on_delete=models.PROTECT,
        related_name="terms",
    )
    number = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(3)]
    )

    class Meta:
        db_table = "grades_term"
        constraints = [
            models.UniqueConstraint(
                fields=["school_year", "number"],
                name="unique_grades_term_school_year_number",
            )
        ]

    def __str__(self) -> str:
        return f"{self.school_year_id}:P{self.number}"


class Activity(ScopedModel):
    """Graded classroom activity (grades spec — Activity Invariants and Tipo)."""

    class ActivityType(models.TextChoices):
        TASK = "task", "Tarea"
        ACTIVITY = "activity", "Actividad"
        PROJECT = "project", "Proyecto"
        EXAM = "exam", "Examen"

    group = models.ForeignKey(
        "schools.Group",
        on_delete=models.PROTECT,
        related_name="activities",
    )
    term = models.ForeignKey(
        Term,
        on_delete=models.PROTECT,
        related_name="activities",
    )
    title = models.CharField(max_length=200)
    activity_type = models.CharField(max_length=20, choices=ActivityType.choices)
    due_date = models.DateField()
    formative_field_id = models.CharField(max_length=64)
    subject_ids = models.JSONField(default=list)
    description = models.TextField(blank=True, default="")

    class Meta:
        db_table = "grades_activity"
        ordering = ["due_date", "pk"]

    def clean(self) -> None:
        super().clean()
        if not self.subject_ids:
            raise ValidationError({"subject_ids": "At least one subject is required."})

    def __str__(self) -> str:
        return f"{self.title} ({self.activity_type})"


class ActivityScore(ScopedModel):
    """Per-student score for an Activity (grades spec — ActivityScore Invariants).

    `null` means unscored and is distinct from `0.0`.
    """

    activity = models.ForeignKey(
        Activity,
        on_delete=models.PROTECT,
        related_name="scores",
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.PROTECT,
        related_name="activity_scores",
    )
    score = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
    )

    class Meta:
        db_table = "grades_activityscore"
        constraints = [
            models.UniqueConstraint(
                fields=["activity", "student"],
                name="unique_grades_activity_student_score",
            )
        ]

    def __str__(self) -> str:
        return f"{self.activity_id}:{self.student_id}={self.score}"
