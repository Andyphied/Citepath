"""Agent investigation service."""

from datetime import UTC, datetime
from uuid import UUID

import structlog

from app.infrastructure.config import Settings, get_settings
from app.infrastructure.db.enums import AgentRunStatus
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
)
from app.modules.agents.tool_executor import ToolExecutor
from app.modules.agents.tool_registry import build_tool_registry
from app.modules.rag.exceptions import ConversationNotFoundError
from app.modules.rag.repository import RAGRepository
from app.modules.rag.schemas import CitationResponse
from app.modules.retrieval.service import RetrievalService
from app.modules.usage.service import UsageService
from app.modules.workspaces.context import WorkspaceContext
from app.modules.workspaces.permissions import PermissionAction, PermissionService

logger = structlog.get_logger(__name__)


class AgentService:
    """Start and retrieve workspace-scoped agent investigations."""

    def __init__(
        self,
        *,
        agent_repository: AgentRepository,
        rag_repository: RAGRepository,
        retrieval_service: RetrievalService,
        completion_provider: ChatCompletionProvider,
        permission_service: PermissionService,
        usage_service: UsageService,
        settings: Settings | None = None,
    ) -> None:
        self._agent_repository = agent_repository
        self._rag_repository = rag_repository
        self._retrieval_service = retrieval_service
        self._completion_provider = completion_provider
        self._permission_service = permission_service
        self._usage_service = usage_service
        self._settings = settings or get_settings()
        registry = build_tool_registry(retrieval_service=retrieval_service)
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

            self._agent_repository.update_run(
                run=run,
                status=AgentRunStatus.COMPLETED,
                result=result_payload,
                step_count=tool_calls_count,
                completed_at=datetime.now(UTC),
            )
            status = AgentRunStatus.COMPLETED.value
        except AgentOrchestrationError as exc:
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
        if run is None or run.user_id != context.user_id:
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
