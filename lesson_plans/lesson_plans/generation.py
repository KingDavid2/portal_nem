"""Prompt assembly for the baseline (no RAG).

The system prompt encodes the NEM/ABPC rules and the fixed 3-fase / 11-momento
skeleton; the user message carries the concrete request plus the hardcoded
contenidos/PDAs the model must reuse verbatim (never invent). The schema itself is
enforced downstream by instructor, so the prompt describes intent, not JSON shape.
"""

from __future__ import annotations

from dataclasses import dataclass

from .schema import ContentPda

# The 11 ABPC momentos across the 3 fases, in canonical order.
ABPC_SKELETON = """\
El proyecto sigue la metodología APRENDIZAJE BASADO EN PROYECTOS COMUNITARIOS (ABPC),
organizada en 3 fases y 11 momentos numerados de forma continua:

Fase 1 — Planeación:
  1. Identificación
  2. Recuperación
  3. Planificación
Fase 2 — Acción:
  4. Acercamiento
  5. Comprensión y producción
  6. Reconocimiento
  7. Concreción
Fase 3 — Intervención:
  8. Integración
  9. Difusión
  10. Consideraciones
  11. Avances"""

SYSTEM_PROMPT = f"""\
Eres un docente experto en la Nueva Escuela Mexicana (NEM) y en el diseño de planeaciones
didácticas para educación secundaria (Fase 6). Generas un proyecto completo listo para el aula,
en español neutro y profesional, apropiado para estudiantes de secundaria.

{ABPC_SKELETON}

Reglas:
- Usa EXCLUSIVAMENTE los contenidos y PDAs que se te proporcionan. No inventes, no reformules ni
  agregues PDAs distintos a los dados: cópialos tal cual en el campo correspondiente.
- Cada momento contiene una o más sesiones; cada sesión tiene una duración en minutos y una
  secuencia de pasos numerados con su dinámica (actividad) descrita para el docente.
- Vincula el proyecto con ejes articuladores de la NEM y justifica cada uno.
- Incluye una rúbrica con criterios evaluados en 4 niveles de logro.
- El propósito, título y actividades deben girar en torno al tema solicitado y conectar con la
  comunidad del estudiante.
"""


@dataclass(frozen=True)
class GenerationRequest:
    """A teacher-realistic request for a proyecto."""

    campo: str
    grade: str
    theme: str


def _render_pdas(groups: list[ContentPda]) -> str:
    lines: list[str] = []
    for group in groups:
        lines.append(f"Contenido: {group.content}")
        for pda in group.pdas:
            lines.append(f"  - PDA: {pda}")
    return "\n".join(lines)


def build_messages(request: GenerationRequest, pdas: list[ContentPda]) -> list[dict[str, str]]:
    """System + user messages for a single generation."""
    user = (
        f"Genera un proyecto ABPC para Fase 6 con estos datos:\n"
        f"- Campo formativo: {request.campo}\n"
        f"- Grado: {request.grade}\n"
        f"- Tema o problemática: {request.theme}\n\n"
        f"Contenidos y PDAs seleccionados (úsalos verbatim, no inventes otros):\n"
        f"{_render_pdas(pdas)}"
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]
