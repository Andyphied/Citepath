"""Idempotent Northstar Cloud demo dataset seed."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select

from app.infrastructure.config import get_settings
from app.infrastructure.db.enums import DocumentStatus
from app.infrastructure.db.session import get_session_factory
from app.infrastructure.storage import create_storage_backend
from app.modules.auth.password import hash_password
from app.modules.auth.repository import AuthRepository
from app.modules.documents.repository import DocumentRepository
from app.modules.ingestion.job_repository import IngestionJobRepository
from app.modules.ingestion.tasks import process_ingestion_job
from app.modules.workspaces.models import Workspace
from app.modules.workspaces.repository import WorkspaceRepository

logger = structlog.get_logger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_DATA_DIR = REPO_ROOT / "demo_data"
DEMO_USER_EMAIL = "demo@northstar.cloud"
DEMO_USER_NAME = "Northstar Demo"
DEMO_WORKSPACE_NAME = "Northstar Cloud"
DEMO_WORKSPACE_SLUG = "northstar-cloud"
DEFAULT_DEMO_PASSWORD = "northstar-demo"


@dataclass(frozen=True)
class DemoDocumentSpec:
    filename: str
    source_type: str


DEMO_DOCUMENTS: tuple[DemoDocumentSpec, ...] = (
    DemoDocumentSpec("billing-api-runbook.md", "runbook"),
    DemoDocumentSpec("auth-service-architecture.md", "architecture"),
    DemoDocumentSpec("deployment-process.md", "process"),
    DemoDocumentSpec("incident-2025-08-billing-502.md", "incident"),
    DemoDocumentSpec("database-migration-plan.md", "plan"),
    DemoDocumentSpec("notification-service-onboarding.md", "onboarding"),
    DemoDocumentSpec("api-gateway-adr.md", "adr"),
    DemoDocumentSpec("service-dependency-map.json", "map"),
)


def _file_type(filename: str) -> str:
    suffix = Path(filename).suffix.lower().lstrip(".")
    if suffix not in {"md", "txt", "pdf", "json"}:
        raise ValueError(f"Unsupported demo file extension: {filename}")
    return suffix


def _find_workspace_by_slug(session, slug: str) -> Workspace | None:
    return session.scalar(select(Workspace).where(Workspace.slug == slug))


def _find_document_by_title(
    document_repository: DocumentRepository,
    *,
    workspace_id: UUID,
    title: str,
) -> object | None:
    for document in document_repository.list_for_workspace(workspace_id=workspace_id):
        if document.title == title:
            return document
    return None


def seed_demo(*, password: str | None = None) -> dict[str, str]:
    """Create demo user, workspace, documents, and run ingestion synchronously."""
    settings = get_settings()
    session = get_session_factory()()
    auth_repository = AuthRepository(session)
    workspace_repository = WorkspaceRepository(session)
    document_repository = DocumentRepository(session)
    job_repository = IngestionJobRepository(session)
    storage_backend = create_storage_backend(settings)

    resolved_password = password or DEFAULT_DEMO_PASSWORD
    user = auth_repository.find_user_by_email(DEMO_USER_EMAIL)
    if user is None:
        user = auth_repository.create_user(
            email=DEMO_USER_EMAIL,
            password_hash=hash_password(resolved_password),
            name=DEMO_USER_NAME,
        )
        logger.info("demo_user_created", email=DEMO_USER_EMAIL)

    workspace = _find_workspace_by_slug(session, DEMO_WORKSPACE_SLUG)
    if workspace is None:
        workspace = workspace_repository.create_workspace_with_owner(
            name=DEMO_WORKSPACE_NAME,
            slug=DEMO_WORKSPACE_SLUG,
            created_by=user.id,
        )
        logger.info(
            "demo_workspace_created",
            workspace_id=str(workspace.id),
            slug=DEMO_WORKSPACE_SLUG,
        )

    indexed_count = 0
    skipped_count = 0

    for spec in DEMO_DOCUMENTS:
        file_path = DEMO_DATA_DIR / spec.filename
        if not file_path.exists():
            raise FileNotFoundError(f"Missing demo fixture: {file_path}")

        title = spec.filename
        existing = _find_document_by_title(
            document_repository,
            workspace_id=workspace.id,
            title=title,
        )
        if existing is not None and existing.status == DocumentStatus.INDEXED:
            skipped_count += 1
            continue

        file_content = file_path.read_bytes()
        document_id = existing.id if existing is not None else uuid4()
        if existing is None:
            storage_key = storage_backend.save(
                workspace_id=workspace.id,
                document_id=document_id,
                filename=spec.filename,
                content=file_content,
            )
            document = document_repository.create(
                id=document_id,
                workspace_id=workspace.id,
                uploaded_by=user.id,
                title=title,
                source_type=spec.source_type,
                file_type=_file_type(spec.filename),
                storage_key=storage_key,
                status=DocumentStatus.UPLOADED,
            )
        else:
            document = existing
            document_repository.update_status(
                document=document,
                status=DocumentStatus.UPLOADED,
            )

        job = job_repository.create(
            workspace_id=workspace.id,
            document_id=document.id,
        )
        process_ingestion_job(
            str(job.id),
            str(workspace.id),
            str(document.id),
        )

        refreshed = document_repository.get_by_id(
            workspace_id=workspace.id,
            id=document.id,
        )
        if refreshed is None or refreshed.status != DocumentStatus.INDEXED:
            latest_job = job_repository.get_latest_for_document(
                workspace_id=workspace.id,
                document_id=document.id,
            )
            status = latest_job.status.value if latest_job else "unknown"
            error = latest_job.error_message if latest_job else None
            raise RuntimeError(
                f"Ingestion failed for {spec.filename}: status={status}, error={error}"
            )

        indexed_count += 1
        logger.info("demo_document_indexed", filename=spec.filename)

    session.close()

    summary = {
        "email": DEMO_USER_EMAIL,
        "password": resolved_password,
        "workspace_slug": DEMO_WORKSPACE_SLUG,
        "workspace_name": DEMO_WORKSPACE_NAME,
        "indexed_documents": str(indexed_count),
        "skipped_documents": str(skipped_count),
    }
    logger.info(
        "demo_seed_completed",
        email=summary["email"],
        workspace_slug=summary["workspace_slug"],
        workspace_name=summary["workspace_name"],
        indexed_documents=summary["indexed_documents"],
        skipped_documents=summary["skipped_documents"],
        password_set=True,
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed Northstar Cloud demo dataset")
    parser.add_argument(
        "--password",
        default=None,
        help="Demo user password (default: northstar-demo or DEMO_SEED_PASSWORD env)",
    )
    args = parser.parse_args(argv)

    import os

    password = args.password or os.getenv("DEMO_SEED_PASSWORD")
    try:
        summary = seed_demo(password=password)
    except Exception:
        logger.exception("demo_seed_failed")
        return 1

    print("Northstar Cloud demo seed complete:")
    for key, value in summary.items():
        if key == "password":
            print(f"  {key}: (set — login with demo user)")
        else:
            print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
