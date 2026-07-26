"""Tests for config.demo_mode — toggle, boot guard, and health exposure.

Mirrors paysys/crm spec/lib/demo_mode_spec.rb. No database required; all state
comes from environment variables and the DEBUG setting override.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from django.test import override_settings

from config import demo_mode
from config.demo_mode import ProductionNotAllowed


class TestDemoModeRequested:
    """demo_mode_requested() — boolean casting of the DEMO_MODE env var."""

    @pytest.mark.parametrize("value", ["true", "True", "TRUE", "1", "yes", "Yes", "on"])
    def test_truthy_spellings(self, value: str) -> None:
        with patch.dict(os.environ, {"DEMO_MODE": value}):
            assert demo_mode.demo_mode_requested() is True

    @pytest.mark.parametrize("value", ["false", "0", "no", "off", ""])
    def test_falsy_spellings(self, value: str) -> None:
        with patch.dict(os.environ, {"DEMO_MODE": value}):
            assert demo_mode.demo_mode_requested() is False

    def test_unset_is_false(self) -> None:
        env = {k: v for k, v in os.environ.items() if k != "DEMO_MODE"}
        with patch.dict(os.environ, env, clear=True):
            assert demo_mode.demo_mode_requested() is False


class TestValidate:
    """validate() — raises ProductionNotAllowed when demo mode requested on non-debug."""

    def test_raises_when_requested_and_debug_false(self) -> None:
        with patch.dict(os.environ, {"DEMO_MODE": "true"}):
            with override_settings(DEBUG=False):
                with pytest.raises(ProductionNotAllowed):
                    demo_mode.validate()

    def test_noop_when_not_requested(self) -> None:
        env = {k: v for k, v in os.environ.items() if k != "DEMO_MODE"}
        with patch.dict(os.environ, env, clear=True):
            with override_settings(DEBUG=False):
                demo_mode.validate()  # should not raise

    def test_noop_when_debug_true(self) -> None:
        with patch.dict(os.environ, {"DEMO_MODE": "true"}):
            with override_settings(DEBUG=True):
                demo_mode.validate()  # should not raise


class TestEnabled:
    """enabled() — defense-in-depth: early False return before any raise."""

    def test_false_when_debug_false_even_if_requested(self) -> None:
        """enabled() returns False and does NOT raise when DEBUG is off.

        The early return is deliberate — a caller can never turn demo mode on
        with DEBUG off, even if the boot guard was somehow bypassed.
        """
        with patch.dict(os.environ, {"DEMO_MODE": "true"}):
            with override_settings(DEBUG=False):
                assert demo_mode.enabled() is False

    def test_false_when_debug_false_and_unset(self) -> None:
        env = {k: v for k, v in os.environ.items() if k != "DEMO_MODE"}
        with patch.dict(os.environ, env, clear=True):
            with override_settings(DEBUG=False):
                assert demo_mode.enabled() is False

    def test_true_when_debug_true_and_requested(self) -> None:
        with patch.dict(os.environ, {"DEMO_MODE": "true"}):
            with override_settings(DEBUG=True):
                assert demo_mode.enabled() is True

    def test_false_when_debug_true_and_unset(self) -> None:
        env = {k: v for k, v in os.environ.items() if k != "DEMO_MODE"}
        with patch.dict(os.environ, env, clear=True):
            with override_settings(DEBUG=True):
                assert demo_mode.enabled() is False
