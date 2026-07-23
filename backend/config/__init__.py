"""Import the Celery app so `@shared_task` decorators bind to it whenever
Django starts (design File Changes: `config/__init__.py` — import celery app).
"""

from .celery import app as celery_app

__all__ = ["celery_app"]
