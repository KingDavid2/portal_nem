"""Tests for DEMO_DEPLOY hosting-posture gate (Quizzy P6 Slice 3).

Validator is pure — called with explicit args, no live Django settings mutation
required for the hardening checks. enabled() uses override_settings.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from django.test import override_settings

from config.demo_mode import (
    DebugNotAllowedInDemoDeploy,
    DemoDeployNotHardened,
    enabled,
    validate_deploy_hardening,
)

_HARDENED = {
    "debug": False,
    "allowed_hosts": ["demo.example.com"],
    "secret_key": "prod-grade-secret-key-not-the-dev-default",
    "caches": {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": "redis://localhost:6379/1",
        },
    },
    "session_cookie_secure": True,
    "csrf_cookie_secure": True,
    "demo_mode": True,
}


class TestValidateDeployHardeningDebug:
    def test_raises_when_debug_true(self) -> None:
        with pytest.raises(DebugNotAllowedInDemoDeploy):
            validate_deploy_hardening(**{**_HARDENED, "debug": True})

    def test_passes_when_debug_false_and_hardened(self) -> None:
        validate_deploy_hardening(**_HARDENED)  # must not raise


class TestValidateDeployHardeningViolations:
    def test_default_secret_key(self) -> None:
        with pytest.raises(DemoDeployNotHardened):
            validate_deploy_hardening(
                **{
                    **_HARDENED,
                    "secret_key": "django-insecure-dev-only-do-not-use-in-production",
                }
            )

    def test_allowed_hosts_star(self) -> None:
        with pytest.raises(DemoDeployNotHardened):
            validate_deploy_hardening(**{**_HARDENED, "allowed_hosts": ["*"]})

    def test_allowed_hosts_localhost_default(self) -> None:
        with pytest.raises(DemoDeployNotHardened):
            validate_deploy_hardening(
                **{**_HARDENED, "allowed_hosts": ["localhost", "127.0.0.1"]}
            )

    def test_non_redis_cache(self) -> None:
        with pytest.raises(DemoDeployNotHardened):
            validate_deploy_hardening(
                **{
                    **_HARDENED,
                    "caches": {
                        "default": {
                            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                            "LOCATION": "x",
                        },
                    },
                }
            )

    def test_session_cookie_insecure(self) -> None:
        with pytest.raises(DemoDeployNotHardened):
            validate_deploy_hardening(**{**_HARDENED, "session_cookie_secure": False})

    def test_csrf_cookie_insecure(self) -> None:
        with pytest.raises(DemoDeployNotHardened):
            validate_deploy_hardening(**{**_HARDENED, "csrf_cookie_secure": False})

    def test_demo_mode_false(self) -> None:
        with pytest.raises(DemoDeployNotHardened):
            validate_deploy_hardening(**{**_HARDENED, "demo_mode": False})


class TestEnabledTruthTable:
    """enabled() = DEMO_MODE ∧ (DEBUG ∨ DEMO_DEPLOY)."""

    @pytest.mark.parametrize(
        ("demo_mode", "debug", "demo_deploy", "expected"),
        [
            (True, True, False, True),
            (True, True, True, True),
            (True, False, True, True),
            (True, False, False, False),
            (False, True, False, False),
            (False, True, True, False),
            (False, False, True, False),
            (False, False, False, False),
        ],
    )
    def test_formula(
        self,
        demo_mode: bool,
        debug: bool,
        demo_deploy: bool,
        expected: bool,
    ) -> None:
        env = {k: v for k, v in os.environ.items() if k != "DEMO_MODE"}
        if demo_mode:
            env["DEMO_MODE"] = "true"
        with patch.dict(os.environ, env, clear=True):
            with override_settings(DEBUG=debug, DEMO_DEPLOY=demo_deploy):
                assert enabled() is expected
