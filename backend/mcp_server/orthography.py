"""Spanish orthography hints for MCP create/update (names).

When typed text looks like a common accent miss (Perez → Pérez), tools return
``needs_orthography_clarification`` instead of writing, until the caller passes
``apply_suggested=true`` or ``keep_as_typed=true``.
"""

from __future__ import annotations

import unicodedata

# Common given names / surnames in MX school contexts (lowercase key → correct form).
_WORD_FIXES: dict[str, str] = {
    "perez": "Pérez",
    "martinez": "Martínez",
    "hernandez": "Hernández",
    "gonzalez": "González",
    "lopez": "López",
    "sanchez": "Sánchez",
    "ramirez": "Ramírez",
    "gomez": "Gómez",
    "jimenez": "Jiménez",
    "vazquez": "Vázquez",
    "vásquez": "Vásquez",
    "diaz": "Díaz",
    "garcia": "García",
    "rodriguez": "Rodríguez",
    "fernandez": "Fernández",
    "alvarez": "Álvarez",
    "gutierrez": "Gutiérrez",
    "munoz": "Muñoz",
    "muñoz": "Muñoz",
    "castañeda": "Castañeda",
    "castaneda": "Castañeda",
    "pena": "Peña",
    "nuñez": "Núñez",
    "nunez": "Núñez",
    "jose": "José",
    "maria": "María",
    "angel": "Ángel",
    "andres": "Andrés",
    "jesus": "Jesús",
    "sebastian": "Sebastián",
    "martin": "Martín",
    "adrian": "Adrián",
    "raul": "Raúl",
    "ramon": "Ramón",
    "hector": "Héctor",
    "cesar": "César",
    "ivan": "Iván",
    "monica": "Mónica",
    "sofia": "Sofía",
    "lucia": "Lucía",
    "ines": "Inés",
}


def _fold(word: str) -> str:
    """Lowercase + strip combining marks for dictionary lookup."""
    nfkd = unicodedata.normalize("NFKD", word)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def _suggest_word(word: str) -> str | None:
    if not word:
        return None
    folded = _fold(word)
    fixed = _WORD_FIXES.get(folded)
    if fixed is None:
        return None
    # Already correctly accented (or identical after fold match with same spelling).
    if word == fixed:
        return None
    # Same letters ignoring accents but wrong accents / missing accents.
    if _fold(word) == _fold(fixed) and word != fixed:
        return fixed
    return None


def suggest_person_name_fields(fields: dict[str, str]) -> list[dict]:
    """Return orthography issues for person-name fields.

    Each issue: ``{field, typed, suggested, message}``.
    """
    issues: list[dict] = []
    for field, value in fields.items():
        if not value or not str(value).strip():
            continue
        parts = str(value).split()
        suggested_parts: list[str] = []
        changed = False
        for part in parts:
            suggestion = _suggest_word(part)
            if suggestion is not None:
                suggested_parts.append(suggestion)
                changed = True
            else:
                suggested_parts.append(part)
        if changed:
            suggested = " ".join(suggested_parts)
            issues.append(
                {
                    "field": field,
                    "typed": value,
                    "suggested": suggested,
                    "message": (
                        f"Posible error ortográfico en {field}: "
                        f"«{value}» → «{suggested}»"
                    ),
                }
            )
    return issues


def orthography_clarification_required(
    *,
    action: str,
    typed: dict,
    suggested: dict,
    issues: list[dict],
) -> dict:
    return {
        "status": "needs_orthography_clarification",
        "action": action,
        "typed": typed,
        "suggested": suggested,
        "issues": issues,
        "message": (
            "Hay posibles errores ortográficos. Pregunta al docente si aplica "
            "la corrección (apply_suggested=true) o conserva lo escrito "
            "(keep_as_typed=true)."
        ),
    }


def resolve_orthography(
    *,
    fields: dict[str, str],
    apply_suggested: bool = False,
    keep_as_typed: bool = False,
    action: str,
) -> tuple[dict[str, str], dict | None]:
    """Return ``(fields_to_use, clarification_or_none)``.

    If issues exist and neither flag is set, clarification is returned and
    fields_to_use is unused by the caller.
    """
    issues = suggest_person_name_fields(fields)
    if not issues:
        return fields, None

    suggested = dict(fields)
    for issue in issues:
        suggested[issue["field"]] = issue["suggested"]

    if apply_suggested is True:
        return suggested, None
    if keep_as_typed is True:
        return fields, None

    return fields, orthography_clarification_required(
        action=action,
        typed=fields,
        suggested=suggested,
        issues=issues,
    )
