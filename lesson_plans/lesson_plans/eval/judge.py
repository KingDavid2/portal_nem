"""Claude-as-judge: score a generated proyecto against the golden reference.

Four axes, 1-5 each: PDA fidelity, structural completeness, coherence, Spanish register.
The judge is always Claude (the strongest available critic), regardless of which provider
produced the candidate. The scoring call is injected so aggregation is unit-testable.
"""

from __future__ import annotations

from typing import Callable

from pydantic import BaseModel, Field

from ..config import Config

_AXES = ("pda_fidelity", "structural_completeness", "coherence", "spanish_register")

JUDGE_SYSTEM = """\
Eres un evaluador experto de planeaciones didácticas de la Nueva Escuela Mexicana (NEM).
Compara la planeación CANDIDATA contra la de REFERENCIA y califica cada eje de 1 (muy deficiente)
a 5 (excelente):
- pda_fidelity: ¿usa los PDAs sin inventarlos ni deformarlos?
- structural_completeness: ¿tiene las 3 fases, 11 momentos, sesiones con duración y pasos, y rúbrica?
- coherence: ¿las actividades son coherentes con el tema, el propósito y entre sí?
- spanish_register: ¿el español es correcto y apropiado para secundaria?
Devuelve un juicio breve (rationale) en español."""


class JudgeScore(BaseModel):
    pda_fidelity: int = Field(ge=1, le=5)
    structural_completeness: int = Field(ge=1, le=5)
    coherence: int = Field(ge=1, le=5)
    spanish_register: int = Field(ge=1, le=5)
    rationale: str

    @property
    def total(self) -> int:
        return sum(getattr(self, axis) for axis in _AXES)


def average_scores(scores: list[JudgeScore]) -> dict[str, float]:
    """Mean of each axis across scores (empty -> zeros)."""
    if not scores:
        return {axis: 0.0 for axis in _AXES}
    return {axis: sum(getattr(s, axis) for s in scores) / len(scores) for axis in _AXES}


# score(golden, candidate) -> JudgeScore
Score = Callable[[str, str], JudgeScore]


class Judge:
    def __init__(self, score: Score) -> None:
        self._score = score

    def evaluate(self, golden: str, candidate: str) -> JudgeScore:
        return self._score(golden, candidate)

    @classmethod
    def from_config(cls, config: Config) -> "Judge":
        import instructor
        from anthropic import Anthropic

        client = instructor.from_anthropic(Anthropic(api_key=config.anthropic_api_key))
        model = config.anthropic_model

        def score(golden: str, candidate: str) -> JudgeScore:
            user = f"=== REFERENCIA ===\n{golden}\n\n=== CANDIDATA ===\n{candidate}"
            return client.messages.create(
                model=model,
                max_tokens=1024,
                system=JUDGE_SYSTEM,
                messages=[{"role": "user", "content": user}],
                response_model=JudgeScore,
            )

        return cls(score=score)
