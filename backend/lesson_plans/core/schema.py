"""Pydantic schema for a NEM ABPC proyecto (Fase 6).

This is the instructor `response_model` and the output contract that survives from
the M1 spike into production. Mirrors the structure verified against
`designs/examples/Ejemplo proyecto ETICA NATURALEZA Y SOCIEDADES.docx`:

    datos -> title/purpose -> articulating axes -> problem -> contenidos+PDAs ->
    3 stages (Planeación/Acción/Intervención) -> 11 momentos -> sessions -> steps ->
    rubric (criteria x 4 achievement levels).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

CCT_PLACEHOLDER = "[ESPACIO PARA SER LLENADO POR EL DOCENTE]"
METHODOLOGY_ABPC = "APRENDIZAJE BASADO EN PROYECTOS COMUNITARIOS"


class ArticulatingAxis(BaseModel):
    """One of the NEM ejes articuladores with the reason it was chosen."""

    name: str
    justification: str


class ContentPda(BaseModel):
    """A SEP contenido and the PDAs (procesos de desarrollo de aprendizaje) under it.

    In Phase A these come verbatim from the hardcoded fixture; the model must not
    invent them. `Proyecto.all_pdas()` flattens these for the fidelity guard.
    """

    content: str
    pdas: list[str]


class Step(BaseModel):
    """A numbered Paso and its Dinámica (the activity description cell)."""

    number: int
    dynamic: str


class Session(BaseModel):
    """One timed block: a `Duración` plus its ordered steps."""

    duration_minutes: int
    steps: list[Step]


class Momento(BaseModel):
    """One of the 11 ABPC momentos, numbered continuously across stages."""

    number: int
    name: str
    sessions: list[Session]


class Stage(BaseModel):
    """A fase: Planeación, Acción, or Intervención."""

    name: str
    momentos: list[Momento]


class RubricCriterion(BaseModel):
    """A rubric row: a criterion described across 4 achievement levels."""

    criterion: str
    levels: list[str]


class Rubric(BaseModel):
    criteria: list[RubricCriterion]


class Datos(BaseModel):
    """The header block. Defaults encode NEM/ABPC constants and the teacher-fill CCT."""

    school_name: str
    cct: str = CCT_PLACEHOLDER
    phase: int = 6
    grade: str
    campo_formativo: str
    methodology: str = METHODOLOGY_ABPC
    date: str


class Proyecto(BaseModel):
    datos: Datos
    title: str
    purpose: str
    articulating_axes: list[ArticulatingAxis]
    problem_or_theme: str
    contents_and_pdas: list[ContentPda]
    stages: list[Stage]
    rubric: Rubric

    def all_pdas(self) -> list[str]:
        """Every PDA string across all contenidos, in order — the fidelity-guard input."""
        return [pda for group in self.contents_and_pdas for pda in group.pdas]
