"""Services layer for Student (school-structure spec — CRUD Gated by
edit_content Capability; Cross-Entity Workspace Consistency Validation).
"""

from django.core.exceptions import PermissionDenied
from django.db import transaction

from students.models import Student
from workspaces.permissions import has_permission


def _require_edit_content(membership) -> None:
    if not has_permission(membership, "edit_content"):
        raise PermissionDenied("Membership lacks edit_content capability.")


def create_student(
    *,
    membership,
    group,
    first_name: str,
    last_name_paternal: str,
    last_name_maternal: str = "",
    curp: str = "",
) -> Student:
    _require_edit_content(membership)
    if group.workspace_id != membership.workspace_id:
        raise ValueError("Group does not belong to the caller's workspace.")
    with transaction.atomic():
        return Student.objects.create(
            workspace=membership.workspace,
            group=group,
            first_name=first_name,
            last_name_paternal=last_name_paternal,
            last_name_maternal=last_name_maternal,
            curp=curp,
        )


def update_student(*, membership, student: Student, **fields) -> Student:
    _require_edit_content(membership)
    if student.workspace_id != membership.workspace_id:
        raise ValueError("Student does not belong to the caller's workspace.")
    if "group" in fields and fields["group"].workspace_id != membership.workspace_id:
        raise ValueError("Group does not belong to the caller's workspace.")
    with transaction.atomic():
        for field, value in fields.items():
            setattr(student, field, value)
        student.save(update_fields=list(fields))
    return student


def delete_student(*, membership, student: Student) -> None:
    _require_edit_content(membership)
    if student.workspace_id != membership.workspace_id:
        raise ValueError("Student does not belong to the caller's workspace.")
    with transaction.atomic():
        student.delete()
