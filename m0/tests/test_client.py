"""Client behavior with a fake OpenAI client — no network."""

import pytest

from m0chat.client import list_models, resolve_model, stream_chat
from m0chat.history import History


class _FakeModels:
    def __init__(self, ids):
        self._ids = ids

    def list(self):
        data = [type("M", (), {"id": i}) for i in self._ids]
        return type("R", (), {"data": data})


class _FakeClient:
    def __init__(self, ids):
        self.models = _FakeModels(ids)


def test_list_models_returns_ids():
    client = _FakeClient(["a/model", "b/model"])
    assert list_models(client) == ["a/model", "b/model"]


def test_resolve_model_keeps_explicit_config_model():
    client = _FakeClient(["served/model"])
    assert resolve_model(client, "chosen/model") == "chosen/model"


def test_resolve_model_defaults_to_first_served_when_unset():
    client = _FakeClient(["first/served", "second"])
    assert resolve_model(client, None) == "first/served"


def test_resolve_model_raises_when_none_served():
    client = _FakeClient([])
    with pytest.raises(RuntimeError):
        resolve_model(client, None)


# --- streaming ---


class _Delta:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.delta = _Delta(content)


class _Chunk:
    def __init__(self, content):
        self.choices = [_Choice(content)]


class _FakeCompletions:
    def __init__(self, chunks):
        self._chunks = chunks
        self.seen_kwargs = None

    def create(self, **kwargs):
        self.seen_kwargs = kwargs
        return iter(self._chunks)


class _FakeChat:
    def __init__(self, chunks):
        self.completions = _FakeCompletions(chunks)


class _StreamClient:
    def __init__(self, chunks):
        self.chat = _FakeChat(chunks)


def test_stream_chat_yields_token_text_and_skips_empty_deltas():
    chunks = [_Chunk("Hola"), _Chunk(None), _Chunk(" mundo")]
    client = _StreamClient(chunks)
    out = list(stream_chat(client, "m", [{"role": "user", "content": "hi"}]))
    assert "".join(out) == "Hola mundo"


def test_stream_chat_requests_streaming_mode():
    client = _StreamClient([_Chunk("x")])
    list(stream_chat(client, "m", [{"role": "user", "content": "hi"}]))
    assert client.chat.completions.seen_kwargs["stream"] is True
    assert client.chat.completions.seen_kwargs["model"] == "m"


# --- history ---


def test_history_appends_and_reset_clears_but_keeps_system():
    h = History(system="be nice")
    assert h.messages() == [{"role": "system", "content": "be nice"}]
    h.add_user("hi")
    h.add_assistant("hello")
    assert len(h.messages()) == 3
    h.reset()
    assert h.messages() == [{"role": "system", "content": "be nice"}]


def test_history_without_system_starts_empty():
    h = History(system=None)
    assert h.messages() == []
    h.add_user("hi")
    assert h.messages() == [{"role": "user", "content": "hi"}]
