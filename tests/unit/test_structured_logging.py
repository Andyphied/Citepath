"""Unit tests for structured logging configuration."""

import json
import logging

import structlog

from app.modules.observability.logging import configure_logging, get_logger


def _reset_logging() -> None:
    structlog.reset_defaults()
    logging.root.handlers.clear()


def test_configure_logging_emits_json_with_level_and_timestamp(capsys) -> None:
    _reset_logging()
    configure_logging()
    logger = get_logger("test")
    logger.info("test_event", request_id="rid-1")

    captured = capsys.readouterr()
    log_entry = json.loads(captured.out.strip())
    assert log_entry["message"] == "test_event"
    assert log_entry["level"] == "info"
    assert log_entry["request_id"] == "rid-1"
    assert "timestamp" in log_entry


def test_configure_logging_is_idempotent(capsys) -> None:
    _reset_logging()
    configure_logging()
    configure_logging()
    logger = get_logger("test")
    logger.info("once")

    captured = capsys.readouterr()
    lines = [line for line in captured.out.strip().split("\n") if line]
    assert len(lines) == 1
