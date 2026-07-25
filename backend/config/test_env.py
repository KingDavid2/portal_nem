"""Precedence contract for the two-layer dotenv load (`config.env`).

`Env.read_env` writes into `environ.Env.ENVIRON` (which *is* `os.environ` in
production), so the tests swap that class attribute for a plain dict: the real
process environment is never mutated and the layers stay observable.
"""

from __future__ import annotations

import environ
import pytest

from config.env import load_env_files


@pytest.fixture
def fake_environ(monkeypatch):
    values: dict[str, str] = {}
    monkeypatch.setattr(environ.Env, "ENVIRON", values)
    return values


def _write(path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def test_repo_root_env_reaches_django(tmp_path, fake_environ):
    _write(tmp_path / ".env", "LLM_BASE_URL=http://root:8000/v1\n")

    load_env_files(tmp_path / "backend")

    assert fake_environ["LLM_BASE_URL"] == "http://root:8000/v1"


def test_backend_env_wins_over_the_repo_root_one(tmp_path, fake_environ):
    _write(tmp_path / ".env", "LLM_MODEL=root-model\nLLM_API_KEY=root-key\n")
    _write(tmp_path / "backend" / ".env", "LLM_MODEL=backend-model\n")

    load_env_files(tmp_path / "backend")

    assert fake_environ["LLM_MODEL"] == "backend-model"
    # The root layer still fills in what the backend layer leaves unset.
    assert fake_environ["LLM_API_KEY"] == "root-key"


def test_process_environment_wins_over_both_files(tmp_path, fake_environ):
    fake_environ["LLM_API_KEY"] = "from-the-shell"
    _write(tmp_path / ".env", "LLM_API_KEY=root-key\n")
    _write(tmp_path / "backend" / ".env", "LLM_API_KEY=backend-key\n")

    load_env_files(tmp_path / "backend")

    assert fake_environ["LLM_API_KEY"] == "from-the-shell"


def test_missing_files_are_a_no_op(tmp_path, fake_environ):
    load_env_files(tmp_path / "backend")

    assert fake_environ == {}
