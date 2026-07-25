"""Render a Proyecto to Markdown for fast terminal/PR review (companion to docx)."""

from __future__ import annotations

from ..schema import Proyecto


def render_md(proyecto: Proyecto) -> str:
    d = proyecto.datos
    out: list[str] = [f"# {proyecto.title}", ""]
    out += [
        f"- **Escuela:** {d.school_name}",
        f"- **CCT:** {d.cct}",
        f"- **Fase:** {d.phase}  **Grado:** {d.grade}",
        f"- **Campo formativo:** {d.campo_formativo}",
        # Omitted on plans generated before the header carried them.
        *([f"- **Asignatura:** {d.subject}"] if d.subject else []),
        *(
            [f"- **Periodo:** {d.start_date} a {d.end_date}"]
            if d.start_date and d.end_date
            else []
        ),
        f"- **Metodología:** {d.methodology}",
        f"- **Problemática o tema:** {proyecto.problem_or_theme}",
        f"- **Fecha:** {d.date}",
        "",
        f"**Propósito:** {proyecto.purpose}",
        "",
        "## Ejes articuladores",
    ]
    out += [f"- **{a.name}:** {a.justification}" for a in proyecto.articulating_axes]

    out += ["", "## Contenidos y PDAs seleccionados"]
    for group in proyecto.contents_and_pdas:
        out.append(f"- {group.content}")
        out += [f"  - {pda}" for pda in group.pdas]

    for stage_idx, stage in enumerate(proyecto.stages, start=1):
        out += ["", f"## Fase {stage_idx}: {stage.name}"]
        for momento in stage.momentos:
            out += ["", f"### Momento {momento.number}: {momento.name}"]
            for session in momento.sessions:
                out += ["", f"**Duración:** {session.duration_minutes} minutos", ""]
                out += [f"{s.number}. {s.dynamic}" for s in session.steps]

    out += ["", "## Rúbrica de evaluación"]
    for crit in proyecto.rubric.criteria:
        levels = " | ".join(crit.levels)
        out.append(f"- **{crit.criterion}:** {levels}")

    return "\n".join(out) + "\n"
