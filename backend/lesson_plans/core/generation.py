"""Prompt assembly for the baseline (no RAG).

The system prompt encodes the NEM/ABPC rules and the fixed 3-fase / 11-momento
skeleton; the user message carries the teacher's own planning context plus the
official contenidos/PDAs she selected, which the model must reuse verbatim
(never invent). The schema itself is enforced downstream by instructor, so the
prompt describes intent, not JSON shape.
"""

from __future__ import annotations

from dataclasses import dataclass

from .schema import ContentPda, Proyecto

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
- Usa EXCLUSIVAMENTE los ejes articuladores que se te proporcionan y redacta una justificación
  para cada uno de ellos.
- Respeta la duración y el escenario indicados: dimensiona el número de sesiones conforme a las
  semanas señaladas y sitúa las actividades en el escenario solicitado.
- Incluye una rúbrica con criterios evaluados en 4 niveles de logro.
- El propósito, título y actividades deben girar en torno al tema solicitado y conectar con la
  comunidad del estudiante.
"""


# Stored `LessonPlan.Scenario` id -> the Spanish wording the teacher reads.
# The model must never see the raw id, so an unknown id is a `KeyError` (which
# the generation task treats as terminal) rather than a silent passthrough.
SCENARIO_LABELS = {
    "classroom": "Aula",
    "school": "Escuela",
    "community": "Comunidad",
}


def scenario_label(scenario_id: str) -> str:
    """Spanish display wording for a stored scenario id."""
    try:
        return SCENARIO_LABELS[scenario_id]
    except KeyError:
        raise KeyError(f"Unsupported scenario: {scenario_id!r}")


@dataclass(frozen=True)
class GenerationRequest:
    """A teacher-realistic request for a proyecto.

    Every field carries text the model is meant to read: catalog ids are
    resolved to their Spanish display names *before* they get here, so the
    prompt never leaks an internal id such as `critical-thinking`.
    """

    campo: str
    grade: str
    theme: str
    subject: str
    duration_weeks: int
    start_date: str
    end_date: str
    scenario: str
    context_diagnosis: str
    cross_cutting_themes: tuple[str, ...]


def stamp_request_context(proyecto: Proyecto, request: GenerationRequest) -> Proyecto:
    """Return `proyecto` with the header's asignatura and period set from `request`.

    The model is told these values but is not the source of truth for them: the
    teacher chose them and the row persists them, so they are written over the
    generated header instead of being trusted to come back intact.
    """
    datos = proyecto.datos.model_copy(
        update={
            "subject": request.subject,
            "start_date": request.start_date,
            "end_date": request.end_date,
        }
    )
    return proyecto.model_copy(update={"datos": datos})


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
        f"- Asignatura: {request.subject}\n"
        f"- Grado: {request.grade}\n"
        f"- Tema o problemática: {request.theme}\n"
        f"- Escenario: {request.scenario}\n"
        f"- Duración: {request.duration_weeks} semanas "
        f"(del {request.start_date} al {request.end_date})\n"
        f"- Diagnóstico del contexto: {request.context_diagnosis}\n"
        f"- Ejes articuladores (úsalos exclusivamente y justifica cada uno): "
        f"{', '.join(request.cross_cutting_themes)}\n\n"
        f"Contenidos y PDAs seleccionados (úsalos verbatim, no inventes otros):\n"
        f"{_render_pdas(pdas)}"
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]
