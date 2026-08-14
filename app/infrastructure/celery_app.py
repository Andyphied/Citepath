"""Celery application for background job processing."""

import os

from celery import Celery

from app.infrastructure.config import get_settings


def create_celery_app() -> Celery:
    """Build a Celery app wired to Redis and MVP task defaults."""
    settings = get_settings()
    app = Celery("atlasops", broker=settings.REDIS_URL)
    app.conf.update(
        task_acks_late=True,
        task_time_limit=600,
        result_backend=None,
        task_always_eager=False,
        # Keep broker queue name aligned with /health/ready Redis LLEN probe (OBS-007).
        task_default_queue=settings.CELERY_DEFAULT_QUEUE,
    )
    return app


# Celery CLI expects a module-level app; bootstrap when runtime env is present.
celery_app: Celery = Celery("atlasops")

if os.getenv("REDIS_URL"):
    from app.infrastructure.db.base import import_all_models

    import_all_models()
    celery_app = create_celery_app()
    import app.modules.ingestion.tasks  # noqa: E402, F401
