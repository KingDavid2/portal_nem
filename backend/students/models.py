from django.db import models

from workspaces.models import ScopedModel


class Student(ScopedModel):
    """A student enrolled in a Group (school-structure spec).

    `group` is `PROTECT` — a leaf record must not be silently destroyed by
    deleting its parent Group. `curp` is indexed but deliberately NOT unique
    (locked design-brief decision — duplicate CURPs are a data-quality issue
    handled outside the DB layer, not a hard constraint).
    """

    group = models.ForeignKey(
        "schools.Group", on_delete=models.PROTECT, related_name="students"
    )
    first_name = models.CharField(max_length=100)
    last_name_paternal = models.CharField(max_length=100)
    last_name_maternal = models.CharField(max_length=100, blank=True)
    curp = models.CharField(max_length=18, blank=True, db_index=True)

    class Meta:
        db_table = "students_student"

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name_paternal}"
