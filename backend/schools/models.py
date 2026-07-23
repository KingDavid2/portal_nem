from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from workspaces.models import ScopedModel


class School(ScopedModel):
    """A physical school site (school-structure spec — Entity Field Shapes)."""

    class Level(models.TextChoices):
        PREESCOLAR = "preescolar", "Preescolar"
        PRIMARIA = "primaria", "Primaria"
        SECUNDARIA = "secundaria", "Secundaria"

    name = models.CharField(max_length=200)
    cct = models.CharField(max_length=10, blank=True)
    level = models.CharField(max_length=20, choices=Level.choices)

    class Meta:
        db_table = "schools_school"

    def __str__(self) -> str:
        return self.name


class SchoolYear(ScopedModel):
    """A school year cycle scoped to one School."""

    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name="school_years"
    )
    label = models.CharField(max_length=9)

    class Meta:
        db_table = "schools_schoolyear"
        constraints = [
            models.UniqueConstraint(
                fields=["school", "label"], name="unique_school_year_label"
            )
        ]

    def __str__(self) -> str:
        return f"{self.school_id}:{self.label}"


class Group(ScopedModel):
    """A grado/grupo classroom group scoped to one SchoolYear."""

    school_year = models.ForeignKey(
        SchoolYear, on_delete=models.CASCADE, related_name="groups"
    )
    grado = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(3)]
    )
    grupo = models.CharField(max_length=1)

    class Meta:
        db_table = "schools_group"
        constraints = [
            models.UniqueConstraint(
                fields=["school_year", "grado", "grupo"],
                name="unique_group_school_year_grado_grupo",
            )
        ]

    def __str__(self) -> str:
        return f"{self.school_year_id}:{self.grado}{self.grupo}"
