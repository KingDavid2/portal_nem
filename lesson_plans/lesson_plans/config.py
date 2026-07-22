"""Config for both providers.

Extends M0's env pattern (`simple_chat_testing/.../config.py`): the OpenAI-compat
side (base_url/model/api_key) drives the self-hosted Qwen path; the Anthropic side
drives the Claude ceiling. Nothing here hardcodes a secret — Anthropic key comes
from the environment, the LAN endpoint needs none.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping, Optional

DEFAULT_BASE_URL = "http://192.168.1.241:8000/v1"
DEFAULT_API_KEY = "dummy"  # vLLM ignores it, but the OpenAI client requires non-empty.
DEFAULT_ANTHROPIC_MODEL = "claude-opus-4-8"


def _clean(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    return value or None


@dataclass(frozen=True)
class Config:
    base_url: str
    model: Optional[str]  # None -> resolve via model discovery
    api_key: str
    anthropic_api_key: Optional[str]
    anthropic_model: str

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "Config":
        env = os.environ if env is None else env
        base_url = _clean(env.get("LLM_BASE_URL")) or DEFAULT_BASE_URL
        return cls(
            base_url=base_url.rstrip("/"),
            model=_clean(env.get("LLM_MODEL")),
            api_key=_clean(env.get("LLM_API_KEY")) or DEFAULT_API_KEY,
            anthropic_api_key=_clean(env.get("ANTHROPIC_API_KEY")),
            anthropic_model=_clean(env.get("ANTHROPIC_MODEL")) or DEFAULT_ANTHROPIC_MODEL,
        )
