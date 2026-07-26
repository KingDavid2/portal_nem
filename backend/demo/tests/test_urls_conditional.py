"""The demo routes must not exist unless demo mode is enabled.

Layer 4 of the safety story in the M5 plan: `config/urls.py` only includes
`demo.urls` when `demo_mode.enabled()` is true, so with the toggle off the
endpoints 404 because they were never registered — not because a permission
check rejected the caller. This test reloads `config.urls` under both states
and restores the module afterwards.
"""

from __future__ import annotations

import importlib
import os
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.urls import URLResolver

import config.urls


def _demo_is_registered(module) -> bool:
    return any(
        isinstance(entry, URLResolver) and str(entry.pattern) == "api/demo/"
        for entry in module.urlpatterns
    )


@pytest.fixture(autouse=True)
def restore_urlconf():
    yield
    importlib.reload(config.urls)


def test_demo_routes_absent_when_demo_mode_is_off():
    env = {k: v for k, v in os.environ.items() if k != "DEMO_MODE"}
    with patch.dict(os.environ, env, clear=True):
        reloaded = importlib.reload(config.urls)

    assert _demo_is_registered(reloaded) is False


def test_demo_routes_present_when_demo_mode_is_on():
    with patch.dict(os.environ, {"DEMO_MODE": "true"}):
        with override_settings(DEBUG=True):
            reloaded = importlib.reload(config.urls)

    assert _demo_is_registered(reloaded) is True
