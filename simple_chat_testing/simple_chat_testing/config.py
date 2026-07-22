"""Config for the OpenAI-compatible transport.

Nothing here names Qwen, vLLM, or an IP as a hard requirement: the base URL and
model come from the environment. Pointing at another OpenAI-compatible endpoint
(a different vLLM box, Ollama, an OpenAI-compat proxy) is a .env edit, never a
code change. This factory is the seed of M1's OpenAICompatProvider.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping, Optional

DEFAULT_BASE_URL = "http://192.168.1.241:8000/v1"
DEFAULT_API_KEY = "dummy"  # vLLM ignores it, but the OpenAI client requires non-empty.


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

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "Config":
        env = os.environ if env is None else env
        base_url = _clean(env.get("LLM_BASE_URL")) or DEFAULT_BASE_URL
        return cls(
            base_url=base_url.rstrip("/"),
            model=_clean(env.get("LLM_MODEL")),
            api_key=_clean(env.get("LLM_API_KEY")) or DEFAULT_API_KEY,
        )
