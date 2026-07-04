"""API tests for user login."""

from pathlib import Path

import jwt
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

try:
    from testcontainers.postgres import PostgresContainer
except ImportError:  # pragma: no cover - optional dev dependency
    PostgresContainer = None

from app.infrastructure.config import reset_settings_cache
from app.infrastructure.db.session import reset_db_engine
from app.infrastructure.rate_limit import reset_login_rate_limiter
from app.main import create_app

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
    reason="Docker is required for auth login API tests",
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
    reset_login_rate_limiter()

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


def _register_user(client: TestClient) -> dict:
    response = client.post(
        "/auth/register",
        json={
            "email": "login-user@example.com",
            "password": "securepass123",
            "name": "Login User",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_login_success(auth_test_context) -> None:
    client, _db_session = auth_test_context
    registered = _register_user(client)

    response = client.post(
        "/auth/login",
        json={
            "email": "Login-User@Example.com",
            "password": "securepass123",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["id"] == registered["user"]["id"]
    assert body["user"]["email"] == "login-user@example.com"
    assert body["user"]["name"] == "Login User"
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


def test_login_invalid_password_returns_401(auth_test_context) -> None:
    client, _db_session = auth_test_context
    _register_user(client)

    response = client.post(
        "/auth/login",
        json={
            "email": "login-user@example.com",
            "password": "wrongpassword",
        },
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "invalid_credentials"
    assert body["error"]["message"] == "Invalid email or password"


def test_login_unknown_email_returns_same_401(auth_test_context) -> None:
    client, _db_session = auth_test_context

    response = client.post(
        "/auth/login",
        json={
            "email": "missing@example.com",
            "password": "securepass123",
        },
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "invalid_credentials"
    assert body["error"]["message"] == "Invalid email or password"


def test_login_short_password_returns_422(auth_test_context) -> None:
    client, _db_session = auth_test_context

    response = client.post(
        "/auth/login",
        json={
            "email": "user@example.com",
            "password": "short",
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert "detail" in body


def test_login_rate_limit_returns_429_on_eleventh_attempt(auth_test_context) -> None:
    client, _db_session = auth_test_context
    reset_login_rate_limiter()
    payload = {
        "email": "missing@example.com",
        "password": "securepass123",
    }

    for _ in range(10):
        response = client.post("/auth/login", json=payload)
        assert response.status_code == 401

    response = client.post("/auth/login", json=payload)

    assert response.status_code == 429
    body = response.json()
    assert body["error"]["code"] == "rate_limited"
    assert body["error"]["message"]
    assert "Retry-After" in response.headers
    assert int(response.headers["Retry-After"]) >= 1


def test_login_malformed_password_hash_returns_401_not_500(
    auth_test_context,
) -> None:
    client, db_session = auth_test_context
    registered = _register_user(client)

    db_session.execute(
        text("UPDATE users SET password_hash = :hash WHERE id = :user_id"),
        {"hash": "not-a-valid-bcrypt-hash", "user_id": registered["user"]["id"]},
    )
    db_session.commit()

    response = client.post(
        "/auth/login",
        json={
            "email": "login-user@example.com",
            "password": "securepass123",
        },
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "invalid_credentials"
