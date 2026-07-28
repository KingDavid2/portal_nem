"""LLM-judge scoring + aggregation. The live judge call is injected here."""

from __future__ import annotations

import pytest

from .judge import Judge, JudgeScore, average_scores, build_judge_prompt


def _score(**overrides) -> JudgeScore:
    base = dict(
        pda_fidelity=4,
        structural_completeness=4,
        coherence=4,
        spanish_register=4,
        rationale="r",
    )
    return JudgeScore(**{**base, **overrides})


def test_score_total_sums_four_axes():
    score = _score(
        pda_fidelity=5, structural_completeness=4, coherence=3, spanish_register=2
    )
    assert score.total == 14


@pytest.mark.parametrize("axis", JudgeScore.AXES)
def test_axes_are_bounded_one_to_five(axis):
    with pytest.raises(ValueError):
        _score(**{axis: 6})
    with pytest.raises(ValueError):
        _score(**{axis: 0})


def test_judge_delegates_to_injected_scorer():
    canned = _score()
    seen: dict[str, str] = {}

    def fake_score(golden: str, candidate: str, official: str) -> JudgeScore:
        seen.update(golden=golden, candidate=candidate, official=official)
        return canned

    out = Judge(score=fake_score).evaluate("GOLDEN", "CANDIDATE", "OFFICIAL")

    assert out is canned
    assert seen == {
        "golden": "GOLDEN",
        "candidate": "CANDIDATE",
        "official": "OFFICIAL",
    }


def test_average_scores_means_each_axis():
    a = _score(pda_fidelity=5, structural_completeness=5, coherence=5, spanish_register=5)
    b = _score(pda_fidelity=1, structural_completeness=3, coherence=3, spanish_register=1)

    avg = average_scores([a, b])

    assert avg == {
        "pda_fidelity": 3.0,
        "structural_completeness": 4.0,
        "coherence": 4.0,
        "spanish_register": 3.0,
    }


def test_average_scores_of_nothing_is_zeros():
    assert average_scores([]) == {axis: 0.0 for axis in JudgeScore.AXES}


def test_prompt_carries_official_pdas_separately_from_the_golden():
    """The golden is a *form* reference whose PDAs differ from the catalog's.

    Grading `pda_fidelity` against it would punish a plan for quoting the
    teacher's actual selection, so the official text is its own labelled block.
    """
    prompt = build_judge_prompt(
        golden="REFERENCIA DE FORMA",
        candidate="PLAN GENERADO",
        official="PDA OFICIAL EXACTO",
    )

    assert "REFERENCIA DE FORMA" in prompt
    assert "PLAN GENERADO" in prompt
    assert "PDA OFICIAL EXACTO" in prompt
    # Ordered so the judge reads the fidelity source before the candidate.
    assert prompt.index("PDA OFICIAL EXACTO") < prompt.index("PLAN GENERADO")
