"""D1 scaffold smoke tests: settings import cleanly and migrations are clean."""

import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


def test_django_settings_import_cleanly():
    import django
    from django.conf import settings

    assert settings.configured or True  # importing config.settings must not raise
    django.setup()
    assert "rest_framework" in settings.INSTALLED_APPS
    assert "drf_spectacular" in settings.INSTALLED_APPS
    assert settings.DATABASES["default"]["ATOMIC_REQUESTS"] is True


def test_migrate_check_reports_no_pending_migrations():
    result = subprocess.run(
        [sys.executable, "manage.py", "migrate", "--check"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
