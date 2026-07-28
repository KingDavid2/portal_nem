"""LLM-as-judge: score a generated proyecto on four axes, 1-5 each.

Ported from the M1 spike with one change of substance. M1 gave the judge two
inputs — the golden reference and the candidate — and asked it to grade PDA
fidelity from that pair. The committed goldens do not support this: their PDAs
are not the catalog's (the Lenguajes reference is about identity and literary
texts, and the Ética one says "mapas mentales" where the catalog says "recursos
gráficos"). Grading fidelity against them would penalize a plan for quoting the
teacher's actual selection.

So the golden is a *form* reference — structure, register, depth — and the
official selection is passed as its own labelled block. The deterministic
`invented_pdas` count from `BaseProvider.generate` remains the hard fidelity
signal; this axis is the soft one.

The scoring call is injected so aggregation stays unit-testable without tokens.
"""

from __future__ import annotations

from typing import Callable, ClassVar

from pydantic import BaseModel, Field

JUDGE_SYSTEM = """\
Eres un evaluador experto de planeaciones didácticas de la Nueva Escuela Mexicana (NEM).
Recibes tres bloques: una planeación de REFERENCIA (solo como ejemplo de forma, estructura
y nivel de detalle), los CONTENIDOS Y PDAS OFICIALES que la docente seleccionó, y la
planeación CANDIDATA que debes calificar.

Califica cada eje de 1 (muy deficiente) a 5 (excelente):
- pda_fidelity: ¿reproduce los PDAs OFICIALES tal cual, sin inventarlos ni deformarlos?
  Compara contra el bloque de PDAs oficiales, NO contra los PDAs de la referencia.
- structural_completeness: ¿tiene las 3 fases, 11 momentos, sesiones con duración y pasos,
  y una rúbrica con criterios en 4 niveles de logro?
- coherence: ¿las actividades son coherentes con el tema, el propósito y entre sí?
- spanish_register: ¿el español es correcto y apropiado para secundaria?

La REFERENCIA sirve para calibrar forma y profundidad; no la uses para juzgar el tema ni
los PDAs, porque puede tratar otro contenido.
Devuelve un juicio breve (rationale) en español."""


class JudgeScore(BaseModel):
    pda_fidelity: int = Field(ge=1, le=5)
    structural_completeness: int = Field(ge=1, le=5)
    coherence: int = Field(ge=1, le=5)
    spanish_register: int = Field(ge=1, le=5)
    rationale: str

    AXES: ClassVar[tuple[str, ...]] = (
        "pda_fidelity",
        "structural_completeness",
        "coherence",
        "spanish_register",
    )

    @property
    def total(self) -> int:
        return sum(getattr(self, axis) for axis in self.AXES)


def average_scores(scores: list[JudgeScore]) -> dict[str, float]:
    """Mean of each axis across `scores` (empty -> zeros)."""
    if not scores:
        return {axis: 0.0 for axis in JudgeScore.AXES}
    return {
        axis: sum(getattr(score, axis) for score in scores) / len(scores)
        for axis in JudgeScore.AXES
    }


def build_judge_prompt(golden: str, candidate: str, official: str) -> str:
    """The user message: form reference, then fidelity source, then candidate.

    The official block sits before the candidate so the judge reads the text it
    must check against before the text it is checking.
    """
    return (
        f"=== REFERENCIA (solo forma) ===\n{golden}\n\n"
        f"=== CONTENIDOS Y PDAS OFICIALES ===\n{official}\n\n"
        f"=== CANDIDATA ===\n{candidate}"
    )


# score(golden, candidate, official) -> JudgeScore
Score = Callable[[str, str, str], JudgeScore]

MAX_TOKENS = 1024


class Judge:
    def __init__(self, score: Score) -> None:
        self._score = score

    def evaluate(self, golden: str, candidate: str, official: str) -> JudgeScore:
        return self._score(golden, candidate, official)

    @classmethod
    def from_settings(cls) -> "Judge":
        """Build the live judge from Django settings.

        Reads `EVAL_JUDGE_MODEL`, deliberately *not* `ANTHROPIC_MODEL`: the
        judge must stay fixed while the generation model is swapped, or every
        previously committed scorecard stops being comparable.
        """
        import instructor
        from anthropic import Anthropic
        from django.conf import settings

        if not settings.ANTHROPIC_API_KEY:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set; the judge cannot run. "
                "Export it or add it to .env."
            )

        client = instructor.from_anthropic(Anthropic(api_key=settings.ANTHROPIC_API_KEY))
        model = settings.EVAL_JUDGE_MODEL

        def score(golden: str, candidate: str, official: str) -> JudgeScore:
            return client.messages.create(
                model=model,
                max_tokens=MAX_TOKENS,
                system=JUDGE_SYSTEM,
                messages=[
                    {
                        "role": "user",
                        "content": build_judge_prompt(golden, candidate, official),
                    }
                ],
                response_model=JudgeScore,
            )

        return cls(score=score)
