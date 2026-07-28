"""On-demand generation-quality evals (Quizzy P2).

Not a pytest suite: `run.py` spends real tokens and real minutes, so it runs
behind `manage.py run_evals` as a gate you invoke deliberately. Only the
token-free parts (scoring aggregation, case resolution, golden loading,
formatting) are covered by the `test_*.py` modules here.
"""
