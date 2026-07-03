"""Unit tests for Docker Compose stack definition."""

from pathlib import Path

import yaml

COMPOSE_PATH = Path(__file__).resolve().parents[2] / "docker-compose.yml"


def test_compose_defines_required_services() -> None:
    compose = yaml.safe_load(COMPOSE_PATH.read_text())

    service_names = set(compose["services"])
    assert {"postgres", "redis", "migrate", "api", "worker"}.issubset(service_names)


def test_compose_api_has_healthcheck_and_migration_dependency() -> None:
    compose = yaml.safe_load(COMPOSE_PATH.read_text())
    api = compose["services"]["api"]

    assert api["depends_on"]["migrate"]["condition"] == "service_completed_successfully"
    assert api["healthcheck"]["test"] == [
        "CMD",
        "curl",
        "-f",
        "http://localhost:8000/health",
    ]


def test_compose_uses_psycopg2_database_url() -> None:
    compose = yaml.safe_load(COMPOSE_PATH.read_text())
    database_url = compose["x-app-environment"]["DATABASE_URL"]

    assert database_url.startswith("postgresql+psycopg2://")
    assert "@postgres:5432/" in database_url


def test_compose_postgres_uses_pgvector_image() -> None:
    compose = yaml.safe_load(COMPOSE_PATH.read_text())

    assert compose["services"]["postgres"]["image"] == "pgvector/pgvector:pg16"
