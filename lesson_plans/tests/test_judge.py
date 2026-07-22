"""LLM-judge scoring + aggregation. The live judge call is injected here."""

from __future__ import annotations

from lesson_plans.eval.judge import Judge, JudgeScore, average_scores


def test_score_total_sums_four_axes():
    s = JudgeScore(
        pda_fidelity=5,
        structural_completeness=4,
        coherence=3,
        spanish_register=2,
        rationale="ok",
    )
    assert s.total == 14


def test_judge_delegates_to_injected_scorer():
    canned = JudgeScore(
        pda_fidelity=4, structural_completeness=4, coherence=4, spanish_register=4, rationale="r"
    )
    seen = {}

    def fake_score(golden: str, candidate: str) -> JudgeScore:
        seen["golden"], seen["candidate"] = golden, candidate
        return canned

    judge = Judge(score=fake_score)
    out = judge.evaluate("GOLDEN TEXT", "CANDIDATE TEXT")
    assert out is canned
    assert seen == {"golden": "GOLDEN TEXT", "candidate": "CANDIDATE TEXT"}


def test_average_scores_means_each_axis():
    a = JudgeScore(pda_fidelity=5, structural_completeness=5, coherence=5, spanish_register=5, rationale="")
    b = JudgeScore(pda_fidelity=1, structural_completeness=3, coherence=3, spanish_register=1, rationale="")
    avg = average_scores([a, b])
    assert avg["pda_fidelity"] == 3.0
    assert avg["structural_completeness"] == 4.0
    assert avg["spanish_register"] == 3.0
