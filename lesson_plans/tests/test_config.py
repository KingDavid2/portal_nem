"""Config extends M0's env pattern with the Anthropic (Claude ceiling) knobs."""

from __future__ import annotations

from lesson_plans.config import (
    DEFAULT_ANTHROPIC_MODEL,
    DEFAULT_BASE_URL,
    DEFAULT_EMBED_BASE_URL,
    DEFAULT_EMBED_MODEL,
    Config,
)


def test_from_env_defaults_when_unset():
    c = Config.from_env(env={})
    assert c.base_url == DEFAULT_BASE_URL
    assert c.model is None
    assert c.api_key == "dummy"
    assert c.anthropic_api_key is None
    assert c.anthropic_model == DEFAULT_ANTHROPIC_MODEL
    assert c.embed_base_url == DEFAULT_EMBED_BASE_URL
    assert c.embed_model == DEFAULT_EMBED_MODEL


def test_from_env_reads_embed_knobs_and_strips_trailing_slash():
    c = Config.from_env(env={"EMBED_BASE_URL": " http://box:8001/v1/ ", "EMBED_MODEL": " e5 "})
    assert c.embed_base_url == "http://box:8001/v1"
    assert c.embed_model == "e5"


def test_from_env_reads_and_trims_and_strips_trailing_slash():
    c = Config.from_env(
        env={
            "LLM_BASE_URL": " http://box:8000/v1/ ",
            "LLM_MODEL": " qwen ",
            "ANTHROPIC_API_KEY": " sk-abc ",
            "ANTHROPIC_MODEL": "claude-opus-4-8",
        }
    )
    assert c.base_url == "http://box:8000/v1"
    assert c.model == "qwen"
    assert c.anthropic_api_key == "sk-abc"
    assert c.anthropic_model == "claude-opus-4-8"


def test_blank_values_fall_back_to_defaults():
    c = Config.from_env(env={"LLM_API_KEY": "   ", "ANTHROPIC_MODEL": ""})
    assert c.api_key == "dummy"
    assert c.anthropic_model == DEFAULT_ANTHROPIC_MODEL
