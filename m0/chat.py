#!/usr/bin/env python3
"""M0 chat CLI — a provider-agnostic connectivity + streaming spike.

Usage:
    python chat.py                       # interactive streaming REPL
    python chat.py --system "..."        # REPL with a system prompt
    python chat.py --once "prompt"       # one-shot (scripted/CI smoke check)
    python chat.py --list-models         # GET {base_url}/models

Config comes from the environment (see .env.example): LLM_BASE_URL, LLM_MODEL,
LLM_API_KEY. Nothing about the endpoint is hardcoded in the flow — swapping to
another OpenAI-compatible server is a .env edit.
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from m0chat.client import build_client, list_models, resolve_model, stream_chat
from m0chat.config import Config
from m0chat.history import History


def _format_usage(usage) -> Optional[str]:
    if usage is None:
        return None
    prompt = getattr(usage, "prompt_tokens", None)
    completion = getattr(usage, "completion_tokens", None)
    total = getattr(usage, "total_tokens", None)
    if prompt is None and completion is None and total is None:
        return None
    return f"[tokens] prompt={prompt} completion={completion} total={total}"


def _run_turn(client, model: str, messages) -> str:
    """Stream one assistant turn to stdout, return the full text."""
    parts: list[str] = []
    captured = {"usage": None}

    def grab(u):
        captured["usage"] = u

    for token in stream_chat(client, model, messages, on_usage=grab):
        parts.append(token)
        sys.stdout.write(token)
        sys.stdout.flush()
    sys.stdout.write("\n")
    line = _format_usage(captured["usage"])
    if line:
        print(line)
    return "".join(parts)


def cmd_list_models(client) -> int:
    for model_id in list_models(client):
        print(model_id)
    return 0


def cmd_once(client, model: str, prompt: str, system: Optional[str]) -> int:
    history = History(system=system)
    history.add_user(prompt)
    _run_turn(client, model, history.messages())
    return 0


def cmd_repl(client, model: str, system: Optional[str]) -> int:
    history = History(system=system)
    print(f"M0 chat — model: {model}")
    print("Type your message. /reset clears history, /exit quits.")
    while True:
        try:
            line = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not line:
            continue
        if line in ("/exit", "/quit"):
            return 0
        if line == "/reset":
            history.reset()
            print("(history reset)")
            continue
        history.add_user(line)
        reply = _run_turn(client, model, history.messages())
        history.add_assistant(reply)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="M0 provider-agnostic testing chat")
    parser.add_argument("--system", help="system prompt")
    parser.add_argument("--once", metavar="PROMPT", help="one-shot prompt, then exit")
    parser.add_argument(
        "--list-models", action="store_true", help="list served models and exit"
    )
    args = parser.parse_args(argv)

    config = Config.from_env()
    client = build_client(config)

    if args.list_models:
        return cmd_list_models(client)

    model = resolve_model(client, config.model)

    if args.once is not None:
        return cmd_once(client, model, args.once, args.system)
    return cmd_repl(client, model, args.system)


if __name__ == "__main__":
    raise SystemExit(main())
