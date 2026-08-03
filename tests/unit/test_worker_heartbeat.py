"""Unit tests for Celery worker heartbeat and queue depth (OBS-007)."""

from unittest.mock import MagicMock, patch

from app.infrastructure.health_checks import get_celery_queue_depth
from app.modules.observability.worker_heartbeat import (
    emit_worker_heartbeat,
    start_worker_heartbeat,
    stop_worker_heartbeat,
)


def test_emit_worker_heartbeat_logs_structured_event() -> None:
    with patch(
        "app.modules.observability.worker_heartbeat.logger",
    ) as mock_logger:
        emit_worker_heartbeat(interval_seconds=300)

    mock_logger.info.assert_called_once_with(
        "worker_heartbeat",
        interval_seconds=300,
        task_name="worker_heartbeat",
    )


def test_start_worker_heartbeat_emits_then_stops() -> None:
    stop_worker_heartbeat()
    sleeps: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        stop_worker_heartbeat()

    with patch(
        "app.modules.observability.worker_heartbeat.emit_worker_heartbeat",
    ) as mock_emit:
        thread = start_worker_heartbeat(
            interval_seconds=60,
            sleep_fn=fake_sleep,
        )
        thread.join(timeout=2.0)

    assert mock_emit.call_count >= 1
    assert sleeps == [60.0]
    stop_worker_heartbeat()


def test_get_celery_queue_depth_reads_redis_llen(minimal_env) -> None:
    client = MagicMock()
    client.llen.return_value = 7

    with (
        patch("redis.from_url", return_value=client),
        patch(
            "app.infrastructure.health_checks.get_settings",
            return_value=MagicMock(
                REDIS_URL="redis://localhost:6379/0",
                CELERY_DEFAULT_QUEUE="celery",
            ),
        ),
    ):
        depth = get_celery_queue_depth()

    assert depth == 7
    client.llen.assert_called_once_with("celery")
    client.close.assert_called_once()


def test_get_celery_queue_depth_returns_none_on_error(minimal_env) -> None:
    with patch("redis.from_url", side_effect=ConnectionError("down")):
        assert get_celery_queue_depth() is None
