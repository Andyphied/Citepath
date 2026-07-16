"""PostgreSQL-backed enum types for core schema."""

import enum

from sqlalchemy import Enum as SAEnum


class WorkspaceRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class DocumentStatus(str, enum.Enum):
    """Document ingestion lifecycle status.

    State machine (worker-driven transitions):

        uploaded --(worker picks up job)--> processing
        processing --(ingestion succeeds)--> indexed
        processing --(ingestion fails)-----> failed
        indexed --(re-index requested)------> processing
        failed --(re-index requested)-------> processing

    API clients receive ``status`` (machine value) and ``status_label``
    (human-readable).
    """

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"

    @property
    def label(self) -> str:
        """Human-readable label for UI and API responses."""
        return _DOCUMENT_STATUS_LABELS[self]


_DOCUMENT_STATUS_LABELS: dict[DocumentStatus, str] = {
    DocumentStatus.UPLOADED: "Uploaded",
    DocumentStatus.PROCESSING: "Processing",
    DocumentStatus.INDEXED: "Indexed",
    DocumentStatus.FAILED: "Failed",
}


class IngestionJobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ConversationMode(str, enum.Enum):
    RAG = "rag"
    AGENT = "agent"


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class AgentRunStatus(str, enum.Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentToolCallStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILED = "failed"


class UsageOperation(str, enum.Enum):
    CHAT_COMPLETION = "chat_completion"
    EMBEDDING = "embedding"
    AGENT_STEP = "agent_step"


class UsageEventStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILED = "failed"


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    return [member.value for member in enum_cls]


workspace_role_enum = SAEnum(
    WorkspaceRole,
    name="workspace_role",
    native_enum=True,
    values_callable=_enum_values,
)
document_status_enum = SAEnum(
    DocumentStatus,
    name="document_status",
    native_enum=True,
    values_callable=_enum_values,
)
ingestion_job_status_enum = SAEnum(
    IngestionJobStatus,
    name="ingestion_job_status",
    native_enum=True,
    values_callable=_enum_values,
)
conversation_mode_enum = SAEnum(
    ConversationMode,
    name="conversation_mode",
    native_enum=True,
    values_callable=_enum_values,
)
message_role_enum = SAEnum(
    MessageRole,
    name="message_role",
    native_enum=True,
    values_callable=_enum_values,
)
agent_run_status_enum = SAEnum(
    AgentRunStatus,
    name="agent_run_status",
    native_enum=True,
    values_callable=_enum_values,
)
agent_tool_call_status_enum = SAEnum(
    AgentToolCallStatus,
    name="agent_tool_call_status",
    native_enum=True,
    values_callable=_enum_values,
)
usage_operation_enum = SAEnum(
    UsageOperation,
    name="usage_operation",
    native_enum=True,
    values_callable=_enum_values,
)
usage_event_status_enum = SAEnum(
    UsageEventStatus,
    name="usage_event_status",
    native_enum=True,
    values_callable=_enum_values,
)
