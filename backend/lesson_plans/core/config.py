"""Config shape for both LLM providers (design D1b).

Trimmed from the M1 spike's `config.py`: the embeddings/RAG fields are dropped
(RAG is OFF for this milestone — see `pdas.py`), and the config *source*
changes. M1 read `os.environ` directly via `Config.from_env()`; production
reads Django settings via `factory.build_provider()` instead, so this module
keeps only the frozen dataclass shape both adapters share.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Config:
    base_url: str
    model: Optional[str]  # None -> resolve via model discovery
    api_key: str
    anthropic_api_key: Optional[str]
    anthropic_model: str
