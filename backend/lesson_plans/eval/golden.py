"""Per-campo reference planeaciones, as committed text.

The source documents live in `designs/examples/`, which is gitignored — reading
them at runtime would work on this machine and fail on every other clone. They
are flattened once (paragraphs plus table cells) and the result is committed
next to this module, so an eval run is reproducible from a fresh checkout.

One golden per campo rather than one global reference: judging a Lenguajes plan
against the Ética example would mark it down for being on-topic.

These are *form* references — structure, depth, register. Their PDAs are not the
frozen catalog's, so fidelity is graded against the official selection instead
(see `judge.py`).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"


@lru_cache(maxsize=None)
def golden_text(field_id: str) -> str:
    """The reference planeación for `field_id`.

    Raises `KeyError` when no golden is committed for the field, matching the
    catalog lookups: an eval with nothing to compare against is a failure, not
    an empty string.
    """
    path = GOLDEN_DIR / f"{field_id}.md"
    if not path.is_file():
        raise KeyError(f"No golden reference committed for field: {field_id!r}")
    return path.read_text(encoding="utf-8")
