"""Config resolution — env-driven, provider-agnostic by construction."""

from m0chat.config import Config


def test_defaults_when_env_empty():
    cfg = Config.from_env({})
    assert cfg.base_url == "http://192.168.1.241:8000/v1"
    assert cfg.model is None  # unset -> resolved via model discovery
    assert cfg.api_key == "dummy"  # non-empty; vLLM ignores it


def test_env_overrides_all_fields():
    cfg = Config.from_env(
        {
            "LLM_BASE_URL": "http://other:9000/v1",
            "LLM_MODEL": "some/model",
            "LLM_API_KEY": "sk-real",
        }
    )
    assert cfg.base_url == "http://other:9000/v1"
    assert cfg.model == "some/model"
    assert cfg.api_key == "sk-real"


def test_blank_env_values_fall_back_to_defaults():
    cfg = Config.from_env({"LLM_BASE_URL": "", "LLM_MODEL": "  ", "LLM_API_KEY": ""})
    assert cfg.base_url == "http://192.168.1.241:8000/v1"
    assert cfg.model is None
    assert cfg.api_key == "dummy"


def test_trailing_slash_stripped_from_base_url():
    cfg = Config.from_env({"LLM_BASE_URL": "http://host/v1/"})
    assert cfg.base_url == "http://host/v1"
