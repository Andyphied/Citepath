"""API tests for user registration."""

from pathlib import Path

import jwt
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

try:
    from testcontainers.postgres import PostgresContainer
except ImportError:  # pragma: no cover - optional dev dependency
    PostgresContainer = None

from app.infrastructure.config import reset_settings_cache
from app.infrastructure.db.session import reset_db_engine
from app.main import create_app
from app.modules.users.models import User

REPO_ROOT = Path(__file__).resolve().parents[2]


def _docker_available() -> bool:
    if PostgresContainer is None:
        return False
    try:
        import docker

        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is required for auth registration API tests",
)


@pytest.fixture(scope="module")
def postgres_url():
    """Start a pgvector-enabled Postgres container for auth API tests."""
    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture
def auth_test_context(postgres_url, minimal_env, monkeypatch):
    """Migrated database, API client, and session with per-test cleanup."""
    monkeypatch.chdir(REPO_ROOT)
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    reset_settings_cache()
    reset_db_engine()

    alembic_cfg = Config(str(REPO_ROOT / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(postgres_url)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = session_factory()

    with TestClient(create_app()) as test_client:
        yield test_client, session

    session.close()
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE users RESTART IDENTITY CASCADE"))
    engine.dispose()
    reset_db_engine()


def test_register_success(auth_test_context) -> None:
    client, db_session = auth_test_context

    response = client.post(
        "/auth/register",
        json={
            "email": "User@Example.com",
            "password": "securepass123",
            "name": "Jane Doe",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "user@example.com"
    assert body["user"]["name"] == "Jane Doe"
    assert "id" in body["user"]
    assert "created_at" in body["user"]
    assert "password" not in body["user"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 24 * 3600
    assert body["access_token"]

    payload = jwt.decode(
        body["access_token"],
        "test-secret-key",
        algorithms=["HS256"],
    )
    assert payload["sub"] == body["user"]["id"]

    user = db_session.scalar(
        select(User).where(User.email == "user@example.com")
    )
    assert user is not None
    assert user.password_hash != "securepass123"
    assert user.password_hash.startswith("$2b$")


def test_register_duplicate_email_returns_409(auth_test_context) -> None:
    client, _db_session = auth_test_context
    payload = {
        "email": "duplicate@example.com",
        "password": "securepass123",
    }
    first = client.post("/auth/register", json=payload)
    assert first.status_code == 201

    second = client.post("/auth/register", json=payload)

    assert second.status_code == 409
    body = second.json()
    assert body["error"]["code"] == "duplicate_email"
    assert body["error"]["message"]


def test_register_short_password_returns_422(auth_test_context) -> None:
    client, _db_session = auth_test_context

    response = client.post(
        "/auth/register",
        json={
            "email": "user@example.com",
            "password": "short",
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert "detail" in body


def test_register_long_password_returns_422(auth_test_context) -> None:
    client, _db_session = auth_test_context

    response = client.post(
        "/auth/register",
        json={
            "email": "user@example.com",
            "password": "a" * 129,
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
