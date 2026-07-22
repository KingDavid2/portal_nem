"""In-process message history for the REPL. /reset keeps the system prompt."""

from __future__ import annotations

from typing import Optional


class History:
    def __init__(self, system: Optional[str] = None) -> None:
        self._system = system
        self._turns: list[dict[str, str]] = []

    def add_user(self, content: str) -> None:
        self._turns.append({"role": "user", "content": content})

    def add_assistant(self, content: str) -> None:
        self._turns.append({"role": "assistant", "content": content})

    def reset(self) -> None:
        self._turns.clear()

    def messages(self) -> list[dict[str, str]]:
        head = [{"role": "system", "content": self._system}] if self._system else []
        return head + list(self._turns)
