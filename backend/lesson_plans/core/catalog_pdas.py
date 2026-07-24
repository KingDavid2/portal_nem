"""Resolve stored catalog ids into the verbatim official curriculum text.

`LessonPlan.content_selections` stores only ids (`catalog.py` owns the text).
Generation needs the text itself, so this module is the single translation
step between the two — and the only place the teacher's selection becomes
prompt input.

Every failure is a `KeyError`: `tasks.py` treats it as terminal, so a row
whose ids no longer resolve fails loudly instead of silently generating
against some other content.
"""

from __future__ import annotations

from .catalog import content_by_id, field_by_id, pda_by_id
from .schema import ContentPda


def content_pdas_for(field_id: str, selections: list[dict]) -> list[ContentPda]:
    """Official contents/PDAs for a stored selection, in selection order.

    Each returned group carries the catalog's verbatim `Content.text` and the
    verbatim `Pda.text` of every selected PDA, in the order the teacher listed
    them.

    Raises `KeyError` when the field, a content id, or a PDA id does not
    resolve, or when a PDA resolves inside the field but hangs off another
    content.
    """
    field = field_by_id(field_id)
    groups: list[ContentPda] = []
    for selection in selections:
        content = content_by_id(field.id, selection["content_id"])
        pdas: list[str] = []
        for pda_id in selection["pda_ids"]:
            pda = pda_by_id(field.id, pda_id)
            if pda.content_id != content.id:
                raise KeyError(
                    f"PDA {pda_id!r} does not belong to content {content.id!r}"
                )
            pdas.append(pda.text)
        groups.append(ContentPda(content=content.text, pdas=pdas))
    return groups
