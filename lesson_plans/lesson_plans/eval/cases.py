"""Teacher-realistic generation requests for the scorecard.

Each case is tied to a campo that has a hardcoded PDA fixture (see pdas.py), so the
baseline can be scored on PDA fidelity without RAG.
"""

from __future__ import annotations

from ..generation import GenerationRequest

CASES: list[GenerationRequest] = [
    GenerationRequest(
        campo="Ética, Naturaleza y Sociedades",
        grade="SEGUNDO",
        theme="La Independencia de México",
    ),
    GenerationRequest(
        campo="Lenguajes",
        grade="PRIMERO",
        theme="El uso correcto de la acentuación en la escritura",
    ),
    GenerationRequest(
        campo="Lenguajes",
        grade="TERCERO",
        theme="La producción de textos argumentativos",
    ),
]
