"""Hardcoded Fase 6 contenidos + PDAs, keyed by campo formativo.

Phase A stand-in for RAG: the baseline feeds these verbatim to the model so PDA
fidelity can be measured before pgvector retrieval exists (Phase B replaces this
module with a similarity query over the real SEP corpus). Content here is drawn
from real NEM Fase 6 curriculum; the Ética set matches the Planeabot example.
"""

from __future__ import annotations

import unicodedata

from .schema import ContentPda

# Canonical display name -> its contenidos/PDAs.
_FIXTURES: dict[str, list[ContentPda]] = {
    "Ética, Naturaleza y Sociedades": [
        ContentPda(
            content="Las gestas de resistencia y los movimientos independentistas.",
            pdas=[
                "Relaciona la Revolución de Independencia de 1810 en nuestro país con el "
                "agotamiento del imperio español para mantener la cohesión de sus colonias "
                "ultramarinas.",
                "Comprende la confluencia de procesos (por ejemplo, las reformas borbónicas) y "
                "hechos (como la invasión napoleónica en España) en la configuración de la lucha "
                "por la Independencia de la Nueva España.",
                "Diseña recursos gráficos capaces de transmitir el conocimiento sobre la "
                "Independencia de México.",
            ],
        ),
    ],
    "Lenguajes": [
        ContentPda(
            content="Recursos lingüísticos y textuales para la comprensión y producción de textos.",
            pdas=[
                "Emplea las reglas de acentuación de palabras agudas, graves, esdrújulas y "
                "sobresdrújulas para escribir con corrección.",
                "Produce textos en los que organiza las ideas en párrafos con coherencia y "
                "cohesión para comunicar información a una audiencia determinada.",
            ],
        ),
    ],
}


def _normalize(text: str) -> str:
    """Casefold and strip accents so lookups are accent/case insensitive."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return stripped.casefold().strip()


_INDEX: dict[str, str] = {_normalize(name): name for name in _FIXTURES}


def available_campos() -> list[str]:
    """Canonical campo names with fixtures, in insertion order."""
    return list(_FIXTURES)


def pdas_for(campo: str) -> list[ContentPda]:
    """Contenidos/PDAs for a campo formativo (accent/case insensitive).

    Raises KeyError listing the available campos when none matches.
    """
    canonical = _INDEX.get(_normalize(campo))
    if canonical is None:
        raise KeyError(f"No PDA fixture for {campo!r}. Available: {available_campos()}")
    return _FIXTURES[canonical]
