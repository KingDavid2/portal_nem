"""Teacher-realistic generation requests, pinned to the frozen catalog.

Each case carries catalog *ids* alongside the prompt-ready `GenerationRequest`,
so PDA text is resolved through `catalog_pdas.content_pdas_for` — the same
translation production uses. A renamed content or PDA id therefore fails the
eval loudly instead of quietly scoring against different curriculum text.

The catalog exposes verified text for only two contents, in two of the four
campos (`catalog.py`), so three cases is the honest ceiling: any more would be
repetition, and a case in a field with no official content could not be graded
on fidelity at all.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.generation import GenerationRequest


@dataclass(frozen=True)
class EvalCase:
    """One scorecard row's input: what to generate, and what it is graded against."""

    id: str
    field_id: str
    # `LessonPlan.content_selections` shape: [{"content_id": ..., "pda_ids": [...]}]
    selections: tuple[dict, ...]
    request: GenerationRequest

    @property
    def selection_list(self) -> list[dict]:
        """`content_pdas_for` takes a list; the case stores a tuple to stay frozen."""
        return [dict(selection) for selection in self.selections]


CASES: tuple[EvalCase, ...] = (
    EvalCase(
        id="ethics-independence-full",
        field_id="ethics-nature-societies",
        selections=(
            {
                "content_id": "ethics-independence",
                "pda_ids": [
                    "ethics-independence-relationship",
                    "ethics-independence-processes",
                    "ethics-independence-graphics",
                ],
            },
        ),
        request=GenerationRequest(
            campo="Ética, Naturaleza y Sociedades",
            grade="SEGUNDO",
            theme="La Independencia de México y su huella en nuestra comunidad",
            subject="Historia",
            duration_weeks=4,
            start_date="2026-09-07",
            end_date="2026-10-02",
            scenario="Comunidad",
            context_diagnosis=(
                "Grupo de 32 estudiantes con lectura de comprensión heterogénea; "
                "varios reconocen fechas cívicas pero no las relacionan con procesos "
                "históricos. Hay acceso limitado a internet en casa."
            ),
            cross_cutting_themes=("Pensamiento crítico", "Interculturalidad crítica"),
        ),
    ),
    EvalCase(
        id="languages-accentuation-single",
        field_id="languages",
        selections=(
            {
                "content_id": "languages-text-resources",
                "pda_ids": ["languages-accentuation"],
            },
        ),
        request=GenerationRequest(
            campo="Lenguajes",
            grade="PRIMERO",
            theme="Escribir con acentuación correcta para que nos entiendan",
            subject="Español",
            duration_weeks=3,
            start_date="2026-09-07",
            end_date="2026-09-25",
            scenario="Aula",
            context_diagnosis=(
                "Grupo de 28 estudiantes que escriben con frecuencia en mensajería "
                "instantánea y omiten acentos; confunden palabras agudas y graves."
            ),
            cross_cutting_themes=(
                "Apropiación de las culturas a través de la lectura y la escritura",
            ),
        ),
    ),
    EvalCase(
        id="languages-text-resources-multi",
        field_id="languages",
        selections=(
            {
                "content_id": "languages-text-resources",
                "pda_ids": ["languages-accentuation", "languages-coherent-texts"],
            },
        ),
        request=GenerationRequest(
            campo="Lenguajes",
            grade="TERCERO",
            theme="Producir textos claros para difundir una causa de la escuela",
            subject="Español",
            duration_weeks=5,
            start_date="2026-09-07",
            end_date="2026-10-09",
            scenario="Escuela",
            context_diagnosis=(
                "Grupo de 30 estudiantes que redactan párrafos sueltos sin conectores; "
                "muestran interés en temas de convivencia escolar."
            ),
            cross_cutting_themes=("Inclusión", "Pensamiento crítico"),
        ),
    ),
)


def case_by_id(case_id: str) -> EvalCase:
    for case in CASES:
        if case.id == case_id:
            return case
    raise KeyError(f"Unknown eval case: {case_id!r}")
