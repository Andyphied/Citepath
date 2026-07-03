"""Unit tests for Celery worker skeleton."""

from app.infrastructure.celery_app import create_celery_app


def test_celery_app_uses_redis_broker(minimal_env) -> None:
    app = create_celery_app()

    assert app.main == "atlasops"
    assert app.conf.broker_url == "redis://localhost:6379/0"
    assert app.conf.result_backend is None
    assert app.conf.task_acks_late is True
    assert app.conf.task_time_limit == 600
