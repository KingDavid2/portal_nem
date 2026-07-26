"""Test URLconf that registers the demo routes unconditionally.

`config/urls.py` only includes `demo.urls` when `demo_mode.enabled()` is true,
and that decision is made once, at URLConf import time. Tests that exercise the
endpoints therefore point `ROOT_URLCONF` at this module instead of trying to
re-import `config.urls` with a patched environment. The conditional wiring in
`config/urls.py` is covered separately by `test_urls_conditional.py`.
"""

from __future__ import annotations

from django.urls import include, path

from config.urls import urlpatterns as base_urlpatterns

urlpatterns = [
    *base_urlpatterns,
    path("api/demo/", include("demo.urls")),
]
