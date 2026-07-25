"""Dotenv loading for the `config` project.

Two layers, most specific first: `backend/.env` then the repo-root `.env`.
`Env.read_env` never overwrites a value that is already set (`overwrite=False`
is its default), so precedence is:

    real process environment  >  backend/.env  >  <repo root>/.env

The root file is the one that actually exists in this repo — it carries the LLM
and embeddings endpoints plus `LESSON_PLAN_MONTHLY_GENERATION_LIMIT` — and
before this layering Django never read it, silently running on the defaults
declared in `settings.py`.

The layering does mean a repo-root key now reaches Django whenever `backend/.env`
leaves it unset, `DATABASE_URL` included. That is the point (one file to edit),
and `backend/.env` remains the override for anything the backend must not share.
"""

from __future__ import annotations

from pathlib import Path

import environ


def load_env_files(base_dir: Path) -> None:
    """Read `base_dir/.env`, then `base_dir.parent/.env`, into the environment.

    A path that does not exist is skipped; neither file is required.
    """
    for env_file in (base_dir / ".env", base_dir.parent / ".env"):
        if env_file.is_file():
            environ.Env.read_env(env_file)
