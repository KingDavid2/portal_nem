"""Root pytest fixtures for the portal_nem backend."""

from __future__ import annotations

import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _clear_cache_between_tests():
    """Reset LocMem/Redis throttle counters so rate-limit state never leaks."""
    cache.clear()
    yield
    cache.clear()
