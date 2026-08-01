"""Schema/description metadata for MCP tools (shared by stdio and Quizzy)."""

from __future__ import annotations

_CONFIRM = {
    "type": "boolean",
    "description": "Must be true to apply the mutation; otherwise returns needs_confirmation.",
}

TOOL_SCHEMAS: dict[str, dict] = {
    "list_groups": {"type": "object", "properties": {}, "additionalProperties": False},
    "list_lesson_plans": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    },
    "get_lesson_plan": {
        "type": "object",
        "properties": {"id": {}},
        "required": ["id"],
        "additionalProperties": False,
    },
    "get_quota": {"type": "object", "properties": {}, "additionalProperties": False},
    "search_catalog": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "default": ""},
            "field": {"type": ["string", "null"], "default": None},
        },
        "additionalProperties": False,
    },
    "get_teaching_context": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    },
    "list_school_years": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    },
    "list_students": {
        "type": "object",
        "properties": {"group_id": {}},
        "additionalProperties": False,
    },
    "create_school": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "level": {"type": "string"},
            "cct": {"type": "string"},
        },
        "required": ["name", "level"],
        "additionalProperties": False,
    },
    "create_school_year": {
        "type": "object",
        "properties": {
            "school_id": {},
            "label": {"type": "string"},
        },
        "required": ["school_id", "label"],
        "additionalProperties": False,
    },
    "create_group": {
        "type": "object",
        "properties": {
            "school_year_id": {},
            "grado": {"type": "integer"},
            "grupo": {"type": "string"},
        },
        "required": ["school_year_id", "grado", "grupo"],
        "additionalProperties": False,
    },
    "create_student": {
        "type": "object",
        "properties": {
            "group_id": {
                "description": (
                    "Optional when last cycle has exactly one group. "
                    "Must belong to school_year_label (default: último ciclo)."
                ),
            },
            "school_year_label": {
                "type": "string",
                "description": (
                    "Omit to use último ciclo (max SchoolYear.label). "
                    "Pass only when the teacher named another cycle."
                ),
            },
            "first_name": {"type": "string"},
            "last_name_paternal": {"type": "string"},
            "last_name_maternal": {"type": "string"},
            "curp": {"type": "string"},
            "apply_suggested": {
                "type": "boolean",
                "description": (
                    "After needs_orthography_clarification, set true to save "
                    "with suggested accents (Pérez, Martínez, …)."
                ),
            },
            "keep_as_typed": {
                "type": "boolean",
                "description": (
                    "After needs_orthography_clarification, set true to save "
                    "exactly as typed without accent fixes."
                ),
            },
        },
        "required": ["first_name", "last_name_paternal"],
        "additionalProperties": False,
    },
    "update_school": {
        "type": "object",
        "properties": {
            "id": {},
            "confirm": _CONFIRM,
            "name": {"type": "string"},
            "cct": {"type": "string"},
            "level": {"type": "string"},
        },
        "required": ["id"],
        "additionalProperties": False,
    },
    "update_school_year": {
        "type": "object",
        "properties": {
            "id": {},
            "confirm": _CONFIRM,
            "label": {"type": "string"},
        },
        "required": ["id"],
        "additionalProperties": False,
    },
    "update_group": {
        "type": "object",
        "properties": {
            "id": {},
            "confirm": _CONFIRM,
            "grado": {"type": "integer"},
            "grupo": {"type": "string"},
        },
        "required": ["id"],
        "additionalProperties": False,
    },
    "update_student": {
        "type": "object",
        "properties": {
            "id": {},
            "confirm": _CONFIRM,
            "first_name": {"type": "string"},
            "last_name_paternal": {"type": "string"},
            "last_name_maternal": {"type": "string"},
            "curp": {"type": "string"},
            "group_id": {},
            "apply_suggested": {"type": "boolean"},
            "keep_as_typed": {"type": "boolean"},
        },
        "required": ["id"],
        "additionalProperties": False,
    },
    "delete_school": {
        "type": "object",
        "properties": {"id": {}, "confirm": _CONFIRM},
        "required": ["id"],
        "additionalProperties": False,
    },
    "delete_school_year": {
        "type": "object",
        "properties": {"id": {}, "confirm": _CONFIRM},
        "required": ["id"],
        "additionalProperties": False,
    },
    "delete_group": {
        "type": "object",
        "properties": {"id": {}, "confirm": _CONFIRM},
        "required": ["id"],
        "additionalProperties": False,
    },
    "delete_student": {
        "type": "object",
        "properties": {"id": {}, "confirm": _CONFIRM},
        "required": ["id"],
        "additionalProperties": False,
    },
}

TOOL_DESCRIPTIONS: dict[str, str] = {
    "list_groups": "List groups in the authenticated workspace.",
    "list_lesson_plans": "List lesson plans in the authenticated workspace.",
    "get_lesson_plan": "Fetch one lesson plan by id (scoped to the workspace).",
    "get_quota": "Return the workspace generation quota card.",
    "search_catalog": "Search the frozen curriculum catalog by normalized substring.",
    "get_teaching_context": (
        "Resolve último ciclo escolar (max SchoolYear.label) and its groups; "
        "default_group_id is set only when exactly one group exists."
    ),
    "list_school_years": "List school years in the authenticated workspace.",
    "list_students": "List students; optional group_id filter.",
    "create_school": "Create a school (no confirm required).",
    "create_school_year": "Create a school year under a school (no confirm).",
    "create_group": "Create a group under a school year (no confirm).",
    "create_student": (
        "Create a student in the último ciclo by default (no confirm). "
        "Omit group_id when default_group_id exists; pass school_year_label "
        "only for an explicitly named older cycle. MUST be called to persist; "
        "never invent a student id. If status is needs_orthography_clarification, "
        "ask the teacher then retry with apply_suggested or keep_as_typed."
    ),
    "update_school": "Update a school; requires confirm=true.",
    "update_school_year": "Update a school year; requires confirm=true.",
    "update_group": "Update a group; requires confirm=true.",
    "update_student": (
        "Update a student; requires confirm=true. Name fields may return "
        "needs_orthography_clarification first."
    ),
    "delete_school": "Delete a school; requires confirm=true.",
    "delete_school_year": "Delete a school year; requires confirm=true.",
    "delete_group": "Delete a group; requires confirm=true.",
    "delete_student": "Delete a student; requires confirm=true.",
}
