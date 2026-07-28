"""The grounding verdict: which rendered PDAs are official, and which are not.

`find_invented_pdas` decides this once, at generation time, and its answer is
persisted. The viewer and the docx renderer then re-apply the same rule per PDA
to mark each rendered line — so the rule lives here rather than on the provider
port. A second copy that drifted would mark an official PDA as invented in an
exported document while the database still called the plan clean.

Pure and framework-free, like the other `core/` modules: no Django, and nothing
imported from `ports/` — the dependency runs the other way.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .schema import ContentPda, Proyecto


def normalize_pda(text: str) -> str:
    """Collapse whitespace + casefold so trivial reformatting is not flagged as invention.

    The LLM may re-wrap, re-case, or add spaces around an official PDA without
    actually inventing content. Normalizing before comparison ensures only
    semantic differences trigger the guard.
    """
    return re.sub(r"\s+", " ", text).strip().casefold()


def find_invented_pdas(proyecto: Proyecto, allowed: list[ContentPda]) -> list[str]:
    """Output PDAs (verbatim) absent from the allowed fixture — the hallucination signal.

    Every PDA the LLM rendered must appear in the teacher's selection after
    normalization. Those that do not are returned verbatim so the audit trail
    shows exactly what was invented, not just that something was.
    """
    allowed_norms = {normalize_pda(pda) for group in allowed for pda in group.pdas}
    return [pda for pda in proyecto.all_pdas() if normalize_pda(pda) not in allowed_norms]


@dataclass(frozen=True)
class GroundingReport:
    """The grounding verdict for a plan: what was checked, what was invented.

    `selected` is the verbatim official text the plan was checked against.
    `invented` is the verbatim output of PDAs absent from that selection.

    An empty `selected` means the plan was never checked against anything, so
    nothing is confirmed official — that is the honest verdict for a plan with
    no persisted selection.
    """

    selected: list[ContentPda]
    invented: list[str]

    def is_official(self, pda: str) -> bool:
        """Return True when `pda` matches the normalized text of any selected PDA.

        A plan with no persisted selection was never checked against anything;
        the honest verdict is that nothing is confirmed official.
        """
        normed = normalize_pda(pda)
        return any(normed == normalize_pda(p) for group in self.selected for p in group.pdas)
