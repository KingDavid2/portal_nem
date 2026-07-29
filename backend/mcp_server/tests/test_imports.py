"""Import guard tests (authorization spec — app named mcp_server, never mcp).

`backend/` is on `sys.path`; a local `mcp` package would shadow the PyPI `mcp` SDK
required by this project. These tests assert the SDK resolves from the correct
location, not from any top-level package under the project root.
"""

from __future__ import annotations

import sys
from pathlib import Path

from django.conf import settings

import mcp


def test_mcp_sdk_resolves_under_sys_prefix():
    """The `mcp` package must live under sys.prefix (site-packages), not backend/.

    If a `backend/mcp/` directory exists, Python would import that instead of
    the SDK because `backend/` is on sys.path. This asserts the SDK comes from
    its proper install location.
    """
    assert mcp.__file__ is not None, "mcp module should have a __file__"
    assert mcp.__file__.startswith(
        sys.prefix
    ), f"mcp must resolve under sys.prefix ({sys.prefix}), got {mcp.__file__}"


def test_mcp_sdk_not_shadowed_by_backend_package():
    """The `mcp` package directory must not be a direct child of backend/.

    `settings.BASE_DIR` is `backend/`. If a package named `mcp` lived there
    (`backend/mcp/`), it would shadow the SDK because `backend/` is on
    sys.path. This checks that the mcp package directory itself is not a
    direct child of BASE_DIR — site-packages or .venv nesting inside BASE_DIR
    is allowed.
    """
    base_dir = Path(settings.BASE_DIR).resolve()
    mcp_dir = Path(mcp.__file__).resolve().parent
    assert (
        mcp_dir.parent != base_dir
    ), f"mcp must not be shadowed by backend/mcp/; resolved to {mcp_dir}"