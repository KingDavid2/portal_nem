"""Teaching-context resolution for Quizzy / MCP (último ciclo escolar)."""

from __future__ import annotations

from lesson_plans.serializers import catalog_group_payload
from schools.models import Group, SchoolYear
from schools.serializers import SchoolYearSerializer


def last_school_year_label() -> str | None:
    """Max lexicographic ``SchoolYear.label`` in the active workspace scope."""
    return SchoolYear.objects.order_by("-label").values_list("label", flat=True).first()


def groups_for_label(label: str) -> list[Group]:
    return list(
        Group.objects.filter(school_year__label=label)
        .select_related("school_year__school")
        .order_by("pk")
    )


def teaching_context_payload() -> dict:
    """Resolve último ciclo + groups; ``default_group_id`` only when exactly one."""
    label = last_school_year_label()
    if label is None:
        return {
            "last_school_year_label": None,
            "school_years": [],
            "groups": [],
            "group_count": 0,
            "default_group_id": None,
        }

    years = list(
        SchoolYear.objects.filter(label=label)
        .select_related("school")
        .order_by("pk")
    )
    groups = groups_for_label(label)
    group_payloads = [catalog_group_payload(g) for g in groups]
    default_group_id = groups[0].pk if len(groups) == 1 else None
    return {
        "last_school_year_label": label,
        "school_years": SchoolYearSerializer(years, many=True).data,
        "groups": group_payloads,
        "group_count": len(groups),
        "default_group_id": default_group_id,
    }


def resolve_group_for_create(
    *,
    group_id=None,
    school_year_label: str | None = None,
) -> Group:
    """Resolve the group for a create, defaulting to the último ciclo escolar.

    - ``school_year_label`` omitted → last lexicographic label in the workspace.
    - ``group_id`` omitted → only when that cycle has exactly one group.
    - ``group_id`` set → must belong to the resolved cycle (rejects older cycles).
    """
    from mcp_server.registry import ToolInputError, ToolNotFoundError

    label = school_year_label or last_school_year_label()
    if label is None:
        raise ToolInputError(
            "No hay ciclo escolar en el workspace. Crea un SchoolYear primero."
        )

    groups = groups_for_label(label)
    if not groups:
        raise ToolInputError(
            f"No hay grupos en el ciclo {label}. Crea un grupo primero."
        )

    if group_id is None:
        if len(groups) == 1:
            return groups[0]
        options = [
            {
                "id": g.pk,
                "grado": g.grado,
                "grupo": g.grupo,
                "school_year_label": g.school_year.label,
            }
            for g in groups
        ]
        raise ToolInputError(
            "Hay varios grupos en el ciclo "
            f"{label}; indica group_id. Opciones: {options}"
        )

    try:
        gid = int(group_id)
    except (TypeError, ValueError) as exc:
        raise ToolInputError("Invalid group_id.") from exc

    for group in groups:
        if group.pk == gid:
            return group

    try:
        foreign = Group.objects.select_related("school_year").get(pk=gid)
    except Group.DoesNotExist as exc:
        raise ToolNotFoundError("Group not found.") from exc

    raise ToolInputError(
        f"El grupo {gid} pertenece al ciclo {foreign.school_year.label}, "
        f"no al ciclo objetivo {label}. "
        "Omite school_year_label para usar el último ciclo, "
        f"o pasa school_year_label=\"{foreign.school_year.label}\" "
        "si el docente pidió ese ciclo explícitamente."
    )
