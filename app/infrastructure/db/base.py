"""SQLAlchemy declarative base and model registry."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""

    pass


def import_all_models() -> None:
    """Import all ORM models so Alembic metadata is complete."""
    import app.modules.agents.models  # noqa: F401
    import app.modules.audit.models  # noqa: F401
    import app.modules.documents.models  # noqa: F401
    import app.modules.ingestion.models  # noqa: F401
    import app.modules.rag.models  # noqa: F401
    import app.modules.usage.models  # noqa: F401
    import app.modules.users.models  # noqa: F401
    import app.modules.workspaces.models  # noqa: F401
