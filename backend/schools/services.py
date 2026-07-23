"""Services layer for School / SchoolYear / Group (school-structure spec —
CRUD Gated by edit_content Capability; Cross-Entity Workspace Consistency
Validation).

Every function is keyword-only, wrapped in `transaction.atomic()`, requires
`has_permission(membership, "edit_content")`, and takes the workspace from
`membership.workspace` — never from client input. Parent-entity workspace
consistency is validated explicitly (never relies on RLS/ScopedManager for
this authorization decision).
"""

from django.core.exceptions import PermissionDenied
from django.db import transaction

from schools.models import Group, School, SchoolYear
from workspaces.permissions import has_permission


def _require_edit_content(membership) -> None:
    if not has_permission(membership, "edit_content"):
        raise PermissionDenied("Membership lacks edit_content capability.")


# --- School ------------------------------------------------------------


def create_school(*, membership, name: str, cct: str = "", level: str) -> School:
    _require_edit_content(membership)
    with transaction.atomic():
        return School.objects.create(
            workspace=membership.workspace, name=name, cct=cct, level=level
        )


def update_school(*, membership, school: School, **fields) -> School:
    _require_edit_content(membership)
    if school.workspace_id != membership.workspace_id:
        raise ValueError("School does not belong to the caller's workspace.")
    with transaction.atomic():
        for field, value in fields.items():
            setattr(school, field, value)
        school.save(update_fields=list(fields))
    return school


def delete_school(*, membership, school: School) -> None:
    _require_edit_content(membership)
    if school.workspace_id != membership.workspace_id:
        raise ValueError("School does not belong to the caller's workspace.")
    with transaction.atomic():
        school.delete()


# --- SchoolYear ----------------------------------------------------------


def create_school_year(*, membership, school: School, label: str) -> SchoolYear:
    _require_edit_content(membership)
    if school.workspace_id != membership.workspace_id:
        raise ValueError("School does not belong to the caller's workspace.")
    with transaction.atomic():
        return SchoolYear.objects.create(
            workspace=membership.workspace, school=school, label=label
        )


def update_school_year(*, membership, school_year: SchoolYear, **fields) -> SchoolYear:
    _require_edit_content(membership)
    if school_year.workspace_id != membership.workspace_id:
        raise ValueError("SchoolYear does not belong to the caller's workspace.")
    with transaction.atomic():
        for field, value in fields.items():
            setattr(school_year, field, value)
        school_year.save(update_fields=list(fields))
    return school_year


def delete_school_year(*, membership, school_year: SchoolYear) -> None:
    _require_edit_content(membership)
    if school_year.workspace_id != membership.workspace_id:
        raise ValueError("SchoolYear does not belong to the caller's workspace.")
    with transaction.atomic():
        school_year.delete()


# --- Group -----------------------------------------------------------------


def create_group(*, membership, school_year: SchoolYear, grado: int, grupo: str) -> Group:
    _require_edit_content(membership)
    if school_year.workspace_id != membership.workspace_id:
        raise ValueError("SchoolYear does not belong to the caller's workspace.")
    with transaction.atomic():
        return Group.objects.create(
            workspace=membership.workspace,
            school_year=school_year,
            grado=grado,
            grupo=grupo,
        )


def update_group(*, membership, group: Group, **fields) -> Group:
    _require_edit_content(membership)
    if group.workspace_id != membership.workspace_id:
        raise ValueError("Group does not belong to the caller's workspace.")
    with transaction.atomic():
        for field, value in fields.items():
            setattr(group, field, value)
        group.save(update_fields=list(fields))
    return group


def delete_group(*, membership, group: Group) -> None:
    _require_edit_content(membership)
    if group.workspace_id != membership.workspace_id:
        raise ValueError("Group does not belong to the caller's workspace.")
    with transaction.atomic():
        group.delete()
