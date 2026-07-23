"""Celery application for the portal_nem backend (M4 design — Celery-backed
generation).

The worker process never runs `TenancyMiddleware`, so it does not inherit any
request-scoped workspace context; tasks in `lesson_plans/tasks.py` MUST
establish their own scope via `workspaces.scope.workspace_scope` before any
scoped read/write (tenancy-isolation spec — "Celery Generation Tasks Must
Establish Their Own Workspace RLS Context").
"""

from __future__ import annotations

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("portal_nem")

# Read CELERY_* settings from Django settings (namespaced `CELERY_`).
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover `tasks.py` modules in each INSTALLED_APPS app (e.g.
# `lesson_plans.tasks`).
app.autodiscover_tasks()
