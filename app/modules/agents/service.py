"""Agent investigation service."""

from datetime import UTC, datetime
from uuid import UUID

import structlog

from app.infrastructure.config import Settings, get_settings
from app.infrastructure.db.enums import AgentRunStatus, WorkspaceRole
from app.infrastructure.llm.completion import ChatCompletionProvider
from app.modules.agents.exceptions import (
    AgentCompletionError,
    AgentOrchestrationError,
    AgentRunNotFoundError,
    EmptyObjectiveError,
)
from app.modules.agents.orchestrator import AgentOrchestrator
from app.modules.agents.repository import AgentRepository
from app.modules.agents.schemas import (
    AgentRunDetailResponse,
    AgentRunRequest,
    AgentRunResponse,
    AgentToolCallListResponse,
    AgentToolCallResponse,
)
from app.modules.agents.tool_executor import ToolExecutor
from app.modules.agents.tool_registry import build_tool_registry
from app.modules.audit.repository import AuditRepository
from app.modules.documents.repository import DocumentRepository
from app.modules.ingestion.repository import IngestionRepository
from app.modules.rag.exceptions import ConversationNotFoundError
from app.modules.rag.repository import RAGRepository
from app.modules.rag.schemas import CitationResponse
from app.modules.retrieval.service import RetrievalService
from app.modules.usage.service import UsageService
from app.modules.workspaces.context import WorkspaceContext
from app.modules.workspaces.permissions import PermissionAction, PermissionService

logger = structlog.get_logger(__name__)

AGENT_RUN_COMPLETED_EVENT = "agent.run_completed"
OBJECTIVE_AUDIT_MAX_CHARS = 200
_ADMIN_ROLES = frozenset({WorkspaceRole.OWNER, WorkspaceRole.ADMIN})


class AgentService:
    """Start and retrieve workspace-scoped agent investigations."""

    def __init__(
        self,
        *,
        agent_repository: AgentRepository,
        rag_repository: RAGRepository,
        retrieval_service: RetrievalService,
        document_repository: DocumentRepository,
        ingestion_repository: IngestionRepository,
        completion_provider: ChatCompletionProvider,
        permission_service: PermissionService,
        usage_service: UsageService,
        audit_repository: AuditRepository,
        settings: Settings | None = None,
    ) -> None:
        self._agent_repository = agent_repository
        self._rag_repository = rag_repository
        self._retrieval_service = retrieval_service
        self._completion_provider = completion_provider
        self._permission_service = permission_service
        self._usage_service = usage_service
        self._audit_repository = audit_repository
        self._settings = settings or get_settings()
        registry = build_tool_registry(
            retrieval_service=retrieval_service,
            document_repository=document_repository,
            ingestion_repository=ingestion_repository,
            completion_provider=completion_provider,
            usage_service=usage_service,
        )
        tool_executor = ToolExecutor(
            registry=registry,
            agent_repository=agent_repository,
        )
        self._orchestrator = AgentOrchestrator(
            agent_repository=agent_repository,
            tool_executor=tool_executor,
            completion_provider=completion_provider,
            usage_service=usage_service,
            registry=registry,
            settings=self._settings,
        )

    def start_investigation(
        self,
        *,
        context: WorkspaceContext,
        request: AgentRunRequest,
        ip_address: str | None = None,
    ) -> AgentRunResponse:
        """Create an agent run, execute the investigation loop, and return results."""
        self._permission_service.require(
            context,
            PermissionAction.RUN_AGENT,
            ip_address=ip_address,
        )

        objective = request.objective.strip()
        if not objective:
            raise EmptyObjectiveError()

        self._validate_conversation_id(
            context=context,
            conversation_id=request.conversation_id,
        )

        run = self._agent_repository.create_run(
            workspace_id=context.workspace_id,
            user_id=context.user_id,
            objective=objective,
            status=AgentRunStatus.RUNNING,
        )

        logger.info(
            "agent_run_started",
            agent_run_id=str(run.id),
            workspace_id=str(context.workspace_id),
            objective_length=len(objective),
        )

        try:
            summary, citations, tool_calls_count = self._orchestrator.run(
                context=context,
                agent_run_id=run.id,
                objective=objective,
            )
            result_payload = summary.model_dump(mode="json")
            if request.conversation_id is not None:
                result_payload["conversation_id"] = str(request.conversation_id)

            self._record_run_completed_audit(
                context=context,
                agent_run_id=run.id,
                objective=objective,
                tool_call_count=tool_calls_count,
                status=AgentRunStatus.COMPLETED,
                ip_address=ip_address,
            )
            self._agent_repository.update_run(
                run=run,
                status=AgentRunStatus.COMPLETED,
                result=result_payload,
                step_count=tool_calls_count,
                completed_at=datetime.now(UTC),
            )
            status = AgentRunStatus.COMPLETED.value
        except AgentOrchestrationError as exc:
            tool_calls_count = self._agent_repository.count_tool_calls(
                workspace_id=context.workspace_id,
                agent_run_id=run.id,
            )
            self._record_run_completed_audit(
                context=context,
                agent_run_id=run.id,
                objective=objective,
                tool_call_count=tool_calls_count,
                status=AgentRunStatus.FAILED,
                ip_address=ip_address,
            )
            self._agent_repository.update_run(
                run=run,
                status=AgentRunStatus.FAILED,
                result={"error": "agent_orchestration_failed", "code": exc.message},
                completed_at=datetime.now(UTC),
            )
            logger.warning(
                "agent_run_failed",
                agent_run_id=str(run.id),
                error_code=exc.message,
            )
            raise
        except AgentCompletionError:
            tool_calls_count = self._agent_repository.count_tool_calls(
                workspace_id=context.workspace_id,
                agent_run_id=run.id,
            )
            self._record_run_completed_audit(
                context=context,
                agent_run_id=run.id,
                objective=objective,
                tool_call_count=tool_calls_count,
                status=AgentRunStatus.FAILED,
                ip_address=ip_address,
            )
            self._agent_repository.update_run(
                run=run,
                status=AgentRunStatus.FAILED,
                result={"error": "agent_completion_failed"},
                completed_at=datetime.now(UTC),
            )
            logger.warning(
                "agent_run_failed",
                agent_run_id=str(run.id),
                error_code="agent_completion_failed",
            )
            raise

        logger.info(
            "agent_run_completed",
            agent_run_id=str(run.id),
            tool_calls_count=tool_calls_count,
        )

        return AgentRunResponse(
            agent_run_id=run.id,
            status=status,
            summary=summary,
            citations=citations,
            tool_calls_count=tool_calls_count,
        )

    def get_run(
        self,
        *,
        context: WorkspaceContext,
        agent_run_id: UUID,
        ip_address: str | None = None,
    ) -> AgentRunDetailResponse:
        """Return an agent run when accessible to the caller."""
        self._permission_service.require(
            context,
            PermissionAction.RUN_AGENT,
            ip_address=ip_address,
        )

        run = self._agent_repository.get_run_by_id(
            workspace_id=context.workspace_id,
            id=agent_run_id,
        )
        if run is None or not self._can_view_run(context=context, run_user_id=run.user_id):
            raise AgentRunNotFoundError()

        citations = _extract_citations_from_tool_calls(
            self._agent_repository.list_tool_calls(
                workspace_id=context.workspace_id,
                agent_run_id=run.id,
            )
        )

        return AgentRunDetailResponse(
            id=run.id,
            workspace_id=run.workspace_id,
            user_id=run.user_id,
            objective=run.objective,
            status=run.status.value,
            result=run.result,
            step_count=run.step_count,
            created_at=run.created_at,
            completed_at=run.completed_at,
            citations=citations,
        )

    def list_tool_calls(
        self,
        *,
        context: WorkspaceContext,
        agent_run_id: UUID,
        ip_address: str | None = None,
    ) -> AgentToolCallListResponse:
        """Return ordered tool calls for a run the caller may inspect."""
        self._permission_service.require(
            context,
            PermissionAction.RUN_AGENT,
            ip_address=ip_address,
        )

        run = self._agent_repository.get_run_by_id(
            workspace_id=context.workspace_id,
            id=agent_run_id,
        )
        if run is None or not self._can_view_run(context=context, run_user_id=run.user_id):
            raise AgentRunNotFoundError()

        tool_calls = self._agent_repository.list_tool_calls(
            workspace_id=context.workspace_id,
            agent_run_id=run.id,
        )
        return AgentToolCallListResponse(
            items=[
                AgentToolCallResponse(
                    id=tool_call.id,
                    tool_name=tool_call.tool_name,
                    input=tool_call.input_,
                    output=tool_call.output,
                    status=(
                        tool_call.status.value
                        if hasattr(tool_call.status, "value")
                        else str(tool_call.status)
                    ),
                    latency_ms=tool_call.latency_ms,
                    created_at=tool_call.created_at,
                )
                for tool_call in tool_calls
            ]
        )

    def _validate_conversation_id(
        self,
        *,
        context: WorkspaceContext,
        conversation_id: UUID | None,
    ) -> None:
        """Reject conversation IDs outside the active workspace or caller ownership."""
        if conversation_id is None:
            return

        conversation = self._rag_repository.get_conversation_by_id(
            workspace_id=context.workspace_id,
            id=conversation_id,
        )
        if conversation is None or conversation.user_id != context.user_id:
            raise ConversationNotFoundError()

    def _can_view_run(self, *, context: WorkspaceContext, run_user_id: UUID) -> bool:
        """Creator always; Owner/Admin may inspect any workspace run (API design)."""
        if run_user_id == context.user_id:
            return True
        return context.role in _ADMIN_ROLES

    def _record_run_completed_audit(
        self,
        *,
        context: WorkspaceContext,
        agent_run_id: UUID,
        objective: str,
        tool_call_count: int,
        status: AgentRunStatus,
        ip_address: str | None,
    ) -> None:
        """Persist agent.run_completed audit event."""
        self._audit_repository.create(
            workspace_id=context.workspace_id,
            actor_user_id=context.user_id,
            event_type=AGENT_RUN_COMPLETED_EVENT,
            metadata={
                "agent_run_id": str(agent_run_id),
                "objective": _truncate_objective(objective),
                "tool_call_count": tool_call_count,
                "status": status.value,
            },
            ip_address=ip_address,
        )


def _truncate_objective(objective: str) -> str:
    if len(objective) <= OBJECTIVE_AUDIT_MAX_CHARS:
        return objective
    return objective[:OBJECTIVE_AUDIT_MAX_CHARS] + "…"


def _extract_citations_from_tool_calls(tool_calls) -> list[CitationResponse]:
    citations: list[CitationResponse] = []
    seen: set[str] = set()
    for tool_call in tool_calls:
        output = tool_call.output or {}
        for item in output.get("citations") or []:
            chunk_id = str(item.get("chunk_id"))
            if chunk_id in seen:
                continue
            seen.add(chunk_id)
            citations.append(
                CitationResponse(
                    chunk_id=UUID(chunk_id),
                    document_id=UUID(str(item["document_id"])),
                    document_title=item.get("document_title"),
                    chunk_preview=str(item.get("chunk_preview", "")),
                    score=float(item.get("score", 0.0)),
                    metadata=item.get("metadata"),
                )
            )
    return citations
