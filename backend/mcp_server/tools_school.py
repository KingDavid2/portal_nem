"""School-structure MCP tools (read + CRUD with confirm-gated update/delete)."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.db.models import ProtectedError

from mcp_server.confirm import confirmation_required, is_confirmed
from mcp_server.context import resolve_group_for_create, teaching_context_payload
from mcp_server.orthography import resolve_orthography
from schools import services as school_services
from schools.models import Group, School, SchoolYear
from schools.serializers import GroupSerializer, SchoolSerializer, SchoolYearSerializer
from students import services as student_services
from students.models import Student
from students.serializers import StudentSerializer
from workspaces.scope import workspace_scope


def _tool_errors():
    from mcp_server.registry import ToolDenied, ToolInputError, ToolNotFoundError

    return ToolDenied, ToolInputError, ToolNotFoundError


def _as_int(value, *, label: str) -> int:
    ToolDenied, ToolInputError, ToolNotFoundError = _tool_errors()
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ToolInputError(f"Invalid {label}.") from exc


def _run_service(fn, **kwargs):
    ToolDenied, ToolInputError, ToolNotFoundError = _tool_errors()
    try:
        return fn(**kwargs)
    except PermissionDenied as exc:
        raise ToolDenied() from exc
    except ValueError as exc:
        raise ToolInputError(str(exc)) from exc
    except (IntegrityError, ProtectedError) as exc:
        raise ToolInputError(str(exc)) from exc


# --- Read ------------------------------------------------------------------


def get_teaching_context(membership, **_kwargs) -> dict:
    with workspace_scope(membership.workspace_id):
        return teaching_context_payload()


def list_school_years(membership, **_kwargs) -> dict:
    with workspace_scope(membership.workspace_id):
        years = list(SchoolYear.objects.order_by("-label", "pk"))
        return {"school_years": SchoolYearSerializer(years, many=True).data}


def list_students(membership, *, group_id=None, **_kwargs) -> dict:
    with workspace_scope(membership.workspace_id):
        qs = Student.objects.order_by("pk")
        if group_id is not None:
            qs = qs.filter(group_id=_as_int(group_id, label="group_id"))
        return {"students": StudentSerializer(list(qs), many=True).data}


# --- School ----------------------------------------------------------------


def create_school(membership, *, name: str, level: str, cct: str = "", **_kwargs) -> dict:
    with workspace_scope(membership.workspace_id):
        school = _run_service(
            school_services.create_school,
            membership=membership,
            name=name,
            cct=cct or "",
            level=level,
        )
        return SchoolSerializer(school).data


def update_school(
    membership,
    *,
    id,
    confirm=False,
    name=None,
    cct=None,
    level=None,
    **_kwargs,
) -> dict:
    ToolDenied, ToolInputError, ToolNotFoundError = _tool_errors()
    with workspace_scope(membership.workspace_id):
        try:
            school = School.objects.get(pk=_as_int(id, label="id"))
        except School.DoesNotExist as exc:
            raise ToolNotFoundError("School not found.") from exc

        fields = {}
        if name is not None:
            fields["name"] = name
        if cct is not None:
            fields["cct"] = cct
        if level is not None:
            fields["level"] = level
        if not fields:
            raise ToolInputError("No fields to update.")

        preview = SchoolSerializer(school).data
        if not is_confirmed(confirm):
            return confirmation_required(
                action="update_school",
                preview={"current": preview, "fields": fields},
            )
        school = _run_service(
            school_services.update_school,
            membership=membership,
            school=school,
            **fields,
        )
        return SchoolSerializer(school).data


def delete_school(membership, *, id, confirm=False, **_kwargs) -> dict:
    ToolDenied, ToolInputError, ToolNotFoundError = _tool_errors()
    with workspace_scope(membership.workspace_id):
        try:
            school = School.objects.get(pk=_as_int(id, label="id"))
        except School.DoesNotExist as exc:
            raise ToolNotFoundError("School not found.") from exc
        preview = SchoolSerializer(school).data
        if not is_confirmed(confirm):
            return confirmation_required(action="delete_school", preview=preview)
        _run_service(
            school_services.delete_school, membership=membership, school=school
        )
        return {"status": "deleted", "id": preview["id"]}


# --- SchoolYear ------------------------------------------------------------


def create_school_year(membership, *, school_id, label: str, **_kwargs) -> dict:
    ToolDenied, ToolInputError, ToolNotFoundError = _tool_errors()
    with workspace_scope(membership.workspace_id):
        try:
            school = School.objects.get(pk=_as_int(school_id, label="school_id"))
        except School.DoesNotExist as exc:
            raise ToolNotFoundError("School not found.") from exc
        year = _run_service(
            school_services.create_school_year,
            membership=membership,
            school=school,
            label=label,
        )
        return SchoolYearSerializer(year).data


def update_school_year(
    membership, *, id, confirm=False, label=None, **_kwargs
) -> dict:
    ToolDenied, ToolInputError, ToolNotFoundError = _tool_errors()
    with workspace_scope(membership.workspace_id):
        try:
            year = SchoolYear.objects.get(pk=_as_int(id, label="id"))
        except SchoolYear.DoesNotExist as exc:
            raise ToolNotFoundError("School year not found.") from exc
        if label is None:
            raise ToolInputError("No fields to update.")
        fields = {"label": label}
        preview = SchoolYearSerializer(year).data
        if not is_confirmed(confirm):
            return confirmation_required(
                action="update_school_year",
                preview={"current": preview, "fields": fields},
            )
        year = _run_service(
            school_services.update_school_year,
            membership=membership,
            school_year=year,
            **fields,
        )
        return SchoolYearSerializer(year).data


def delete_school_year(membership, *, id, confirm=False, **_kwargs) -> dict:
    ToolDenied, ToolInputError, ToolNotFoundError = _tool_errors()
    with workspace_scope(membership.workspace_id):
        try:
            year = SchoolYear.objects.get(pk=_as_int(id, label="id"))
        except SchoolYear.DoesNotExist as exc:
            raise ToolNotFoundError("School year not found.") from exc
        preview = SchoolYearSerializer(year).data
        if not is_confirmed(confirm):
            return confirmation_required(action="delete_school_year", preview=preview)
        _run_service(
            school_services.delete_school_year,
            membership=membership,
            school_year=year,
        )
        return {"status": "deleted", "id": preview["id"]}


# --- Group -----------------------------------------------------------------


def create_group(
    membership, *, school_year_id, grado: int, grupo: str, **_kwargs
) -> dict:
    ToolDenied, ToolInputError, ToolNotFoundError = _tool_errors()
    with workspace_scope(membership.workspace_id):
        try:
            year = SchoolYear.objects.get(
                pk=_as_int(school_year_id, label="school_year_id")
            )
        except SchoolYear.DoesNotExist as exc:
            raise ToolNotFoundError("School year not found.") from exc
        group = _run_service(
            school_services.create_group,
            membership=membership,
            school_year=year,
            grado=int(grado),
            grupo=grupo,
        )
        return GroupSerializer(group).data


def update_group(
    membership,
    *,
    id,
    confirm=False,
    grado=None,
    grupo=None,
    **_kwargs,
) -> dict:
    ToolDenied, ToolInputError, ToolNotFoundError = _tool_errors()
    with workspace_scope(membership.workspace_id):
        try:
            group = Group.objects.get(pk=_as_int(id, label="id"))
        except Group.DoesNotExist as exc:
            raise ToolNotFoundError("Group not found.") from exc
        fields = {}
        if grado is not None:
            fields["grado"] = int(grado)
        if grupo is not None:
            fields["grupo"] = grupo
        if not fields:
            raise ToolInputError("No fields to update.")
        preview = GroupSerializer(group).data
        if not is_confirmed(confirm):
            return confirmation_required(
                action="update_group",
                preview={"current": preview, "fields": fields},
            )
        group = _run_service(
            school_services.update_group,
            membership=membership,
            group=group,
            **fields,
        )
        return GroupSerializer(group).data


def delete_group(membership, *, id, confirm=False, **_kwargs) -> dict:
    ToolDenied, ToolInputError, ToolNotFoundError = _tool_errors()
    with workspace_scope(membership.workspace_id):
        try:
            group = Group.objects.get(pk=_as_int(id, label="id"))
        except Group.DoesNotExist as exc:
            raise ToolNotFoundError("Group not found.") from exc
        preview = GroupSerializer(group).data
        if not is_confirmed(confirm):
            return confirmation_required(action="delete_group", preview=preview)
        _run_service(
            school_services.delete_group, membership=membership, group=group
        )
        return {"status": "deleted", "id": preview["id"]}


# --- Student ---------------------------------------------------------------


def create_student(
    membership,
    *,
    first_name: str,
    last_name_paternal: str,
    group_id=None,
    school_year_label: str | None = None,
    last_name_maternal: str = "",
    curp: str = "",
    apply_suggested: bool = False,
    keep_as_typed: bool = False,
    **_kwargs,
) -> dict:
    """Create a student in the último ciclo by default.

    ``group_id`` is optional when that cycle has exactly one group.
    Pass ``school_year_label`` only when the teacher named another cycle.
    Orthography: missing accents (Perez→Pérez) pause for clarification unless
    ``apply_suggested`` or ``keep_as_typed`` is true.
    """
    name_fields = {
        "first_name": first_name,
        "last_name_paternal": last_name_paternal,
        "last_name_maternal": last_name_maternal or "",
    }
    resolved, clarification = resolve_orthography(
        fields=name_fields,
        apply_suggested=apply_suggested,
        keep_as_typed=keep_as_typed,
        action="create_student",
    )
    if clarification is not None:
        return clarification

    with workspace_scope(membership.workspace_id):
        group = resolve_group_for_create(
            group_id=group_id,
            school_year_label=school_year_label,
        )
        student = _run_service(
            student_services.create_student,
            membership=membership,
            group=group,
            first_name=resolved["first_name"],
            last_name_paternal=resolved["last_name_paternal"],
            last_name_maternal=resolved.get("last_name_maternal") or "",
            curp=curp or "",
        )
        payload = StudentSerializer(student).data
        # Agent-facing cycle echo so the model cannot invent a wrong year.
        payload["school_year_label"] = group.school_year.label
        return payload


def update_student(
    membership,
    *,
    id,
    confirm=False,
    first_name=None,
    last_name_paternal=None,
    last_name_maternal=None,
    curp=None,
    group_id=None,
    apply_suggested: bool = False,
    keep_as_typed: bool = False,
    **_kwargs,
) -> dict:
    ToolDenied, ToolInputError, ToolNotFoundError = _tool_errors()
    with workspace_scope(membership.workspace_id):
        try:
            student = Student.objects.get(pk=_as_int(id, label="id"))
        except Student.DoesNotExist as exc:
            raise ToolNotFoundError("Student not found.") from exc

        fields = {}
        if first_name is not None:
            fields["first_name"] = first_name
        if last_name_paternal is not None:
            fields["last_name_paternal"] = last_name_paternal
        if last_name_maternal is not None:
            fields["last_name_maternal"] = last_name_maternal
        if curp is not None:
            fields["curp"] = curp
        if group_id is not None:
            try:
                fields["group"] = Group.objects.get(
                    pk=_as_int(group_id, label="group_id")
                )
            except Group.DoesNotExist as exc:
                raise ToolNotFoundError("Group not found.") from exc
        if not fields:
            raise ToolInputError("No fields to update.")

        name_fields = {
            k: v
            for k, v in fields.items()
            if k in ("first_name", "last_name_paternal", "last_name_maternal")
            and isinstance(v, str)
        }
        if name_fields:
            resolved, clarification = resolve_orthography(
                fields=name_fields,
                apply_suggested=apply_suggested,
                keep_as_typed=keep_as_typed,
                action="update_student",
            )
            if clarification is not None:
                return clarification
            fields.update(resolved)

        preview = StudentSerializer(student).data
        preview_fields = {
            k: (v.pk if k == "group" else v) for k, v in fields.items()
        }
        if not is_confirmed(confirm):
            return confirmation_required(
                action="update_student",
                preview={"current": preview, "fields": preview_fields},
            )
        student = _run_service(
            student_services.update_student,
            membership=membership,
            student=student,
            **fields,
        )
        return StudentSerializer(student).data


def delete_student(membership, *, id, confirm=False, **_kwargs) -> dict:
    ToolDenied, ToolInputError, ToolNotFoundError = _tool_errors()
    with workspace_scope(membership.workspace_id):
        try:
            student = Student.objects.get(pk=_as_int(id, label="id"))
        except Student.DoesNotExist as exc:
            raise ToolNotFoundError("Student not found.") from exc
        preview = StudentSerializer(student).data
        if not is_confirmed(confirm):
            return confirmation_required(action="delete_student", preview=preview)
        _run_service(
            student_services.delete_student,
            membership=membership,
            student=student,
        )
        return {"status": "deleted", "id": preview["id"]}
