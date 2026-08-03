"""Celery worker heartbeat structured logging (OBS-007)."""

from __future__ import annotations

import threading
from typing import Callable

import structlog

logger = structlog.get_logger(__name__)

_heartbeat_thread: threading.Thread | None = None
_stop_event = threading.Event()
_celery_heartbeat_registered = False


def emit_worker_heartbeat(*, interval_seconds: int) -> None:
    """Emit one structured worker heartbeat log line."""
    logger.info(
        "worker_heartbeat",
        interval_seconds=interval_seconds,
        task_name="worker_heartbeat",
    )


def _heartbeat_loop(
    *,
    interval_seconds: int,
    stop_event: threading.Event,
    sleep_fn: Callable[[float], None],
) -> None:
    while not stop_event.is_set():
        emit_worker_heartbeat(interval_seconds=interval_seconds)
        sleep_fn(float(interval_seconds))


def start_worker_heartbeat(
    *,
    interval_seconds: int,
    sleep_fn: Callable[[float], None] | None = None,
) -> threading.Thread:
    """Start a daemon thread that logs a heartbeat every ``interval_seconds``."""
    global _heartbeat_thread

    if interval_seconds < 1:
        raise ValueError("interval_seconds must be >= 1")

    stop_worker_heartbeat()
    _stop_event.clear()

    def default_sleep(seconds: float) -> None:
        _stop_event.wait(seconds)

    sleeper = sleep_fn or default_sleep
    thread = threading.Thread(
        target=_heartbeat_loop,
        kwargs={
            "interval_seconds": interval_seconds,
            "stop_event": _stop_event,
            "sleep_fn": sleeper,
        },
        name="atlasops-worker-heartbeat",
        daemon=True,
    )
    thread.start()
    _heartbeat_thread = thread
    logger.info(
        "worker_heartbeat_started",
        interval_seconds=interval_seconds,
    )
    return thread


def stop_worker_heartbeat() -> None:
    """Stop a previously started heartbeat thread (tests / shutdown)."""
    global _heartbeat_thread
    _stop_event.set()
    thread = _heartbeat_thread
    if thread is not None and thread.is_alive():
        thread.join(timeout=1.0)
    _heartbeat_thread = None


def register_celery_heartbeat(celery_app) -> None:
    """Attach heartbeat startup to Celery ``worker_ready`` signal (once)."""
    global _celery_heartbeat_registered
    if _celery_heartbeat_registered:
        return

    from celery.signals import worker_ready

    @worker_ready.connect(weak=False)
    def _on_worker_ready(**_kwargs) -> None:
        from app.infrastructure.config import get_settings

        settings = get_settings()
        start_worker_heartbeat(
            interval_seconds=settings.WORKER_HEARTBEAT_INTERVAL_SECONDS,
        )

    _celery_heartbeat_registered = True
    _ = celery_app  # app retained for call-site clarity / future binding
