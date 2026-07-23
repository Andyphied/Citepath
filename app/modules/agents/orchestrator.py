"""Agent orchestration loop: plan, tool call, observe, summarize."""

from __future__ import annotations

import json
import time
from typing import Any
from uuid import UUID

import structlog

from app.infrastructure.config import Settings
from app.infrastructure.llm.completion import ChatCompletionProvider
from app.modules.agents.completion import complete_agent_step, parse_json_content
from app.modules.agents.exceptions import (
    AgentCompletionError,
    AgentOrchestrationError,
    UnknownToolError,
)
from app.modules.agents.objective_parser import parse_objective
from app.modules.agents.repository import AgentRepository
from app.modules.agents.schemas import AgentPlanAction, InvestigationSummary
from app.modules.agents.tool_executor import ToolExecutor
from app.modules.agents.tool_registry import RegisteredTool, tool_schemas
from app.modules.rag.schemas import CitationResponse
from app.modules.usage.service import UsageService
from app.modules.workspaces.context import WorkspaceContext

logger = structlog.get_logger(__name__)

MAX_AGENT_STEPS = 8
RUN_TIMEOUT_SECONDS = 120

INSUFFICIENT_CONTEXT_SUMMARY_TEXT = (
    "Insufficient workspace evidence was found to produce a grounded investigation "
    "summary. Index relevant runbooks or incident notes and retry."
)


def build_insufficient_context_summary(objective: str) -> InvestigationSummary:
    """Return a safe structured summary when no grounded citations exist."""
    return InvestigationSummary(
        problem_statement=objective,
        summary=INSUFFICIENT_CONTEXT_SUMMARY_TEXT,
        likely_causes=[],
        likely_related_systems=[],
        recommended_checks=[],
        related_documents=[],
        action_items=[],
        risks_or_unknowns=[
            "No grounded citations were available for this investigation",
        ],
        next_steps=[
            "Confirm relevant documents are indexed in this workspace",
            "Retry with a more specific objective",
        ],
    )


class AgentOrchestrator:
    """Run the incident investigation tool loop and produce a structured summary."""

    def __init__(
        self,
        *,
        agent_repository: AgentRepository,
        tool_executor: ToolExecutor,
        completion_provider: ChatCompletionProvider,
        usage_service: UsageService,
        registry: dict[str, RegisteredTool],
        settings: Settings,
    ) -> None:
        self._agent_repository = agent_repository
        self._tool_executor = tool_executor
        self._completion_provider = completion_provider
        self._usage_service = usage_service
        self._registry = registry
        self._settings = settings

    def run(
        self,
        *,
        context: WorkspaceContext,
        agent_run_id: UUID,
        objective: str,
    ) -> tuple[InvestigationSummary, list[CitationResponse], int]:
        """Execute the agent loop and return summary, citations, and tool call count."""
        started_at = time.monotonic()
        parsed = parse_objective(objective)
        observations: list[dict[str, Any]] = []
        aggregated_citations: list[CitationResponse] = []
        seen_chunk_ids: set[str] = set()
        steps_taken = 0

        for step in range(1, MAX_AGENT_STEPS + 1):
            if time.monotonic() - started_at > RUN_TIMEOUT_SECONDS:
                raise AgentOrchestrationError("timeout_exceeded")

            plan = self._plan_next_step(
                context=context,
                agent_run_id=agent_run_id,
                objective=objective,
                parsed_objective=parsed,
                observations=observations,
                step=step,
            )

            if plan.action == "finish":
                break

            if plan.tool_name is None:
                raise AgentOrchestrationError("missing_tool_name")

            try:
                output = self._tool_executor.run(
                    tool_name=plan.tool_name,
                    arguments=plan.arguments,
                    context=context,
                    agent_run_id=agent_run_id,
                )
            except UnknownToolError as exc:
                raise AgentOrchestrationError("unknown_tool") from exc

            steps_taken += 1
            observations.append(
                {
                    "step": step,
                    "tool_name": plan.tool_name,
                    "arguments": plan.arguments or {},
                    "output": output,
                }
            )
            for citation in output.get("citations") or []:
                chunk_id = str(citation.get("chunk_id"))
                if chunk_id in seen_chunk_ids:
                    continue
                seen_chunk_ids.add(chunk_id)
                aggregated_citations.append(
                    CitationResponse(
                        chunk_id=UUID(chunk_id),
                        document_id=UUID(str(citation["document_id"])),
                        document_title=citation.get("document_title"),
                        chunk_preview=str(citation.get("chunk_preview", "")),
                        score=float(citation.get("score", 0.0)),
                        metadata=citation.get("metadata"),
                    )
                )

        summary = self._generate_summary(
            context=context,
            agent_run_id=agent_run_id,
            objective=objective,
            observations=observations,
            citations=aggregated_citations,
            max_steps_reached=steps_taken >= MAX_AGENT_STEPS,
        )

        tool_calls_count = self._agent_repository.count_tool_calls(
            workspace_id=context.workspace_id,
            agent_run_id=agent_run_id,
        )
        return summary, aggregated_citations, tool_calls_count

    def _plan_next_step(
        self,
        *,
        context: WorkspaceContext,
        agent_run_id: UUID,
        objective: str,
        parsed_objective: dict[str, list[str]],
        observations: list[dict[str, Any]],
        step: int,
    ) -> AgentPlanAction:
        tools_json = json.dumps(tool_schemas(self._registry), indent=2)
        observations_json = json.dumps(observations, indent=2)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an incident investigation agent. Choose the next action using "
                    "ONLY whitelisted tools. Respond with JSON: "
                    '{"action":"call_tool"|"finish","tool_name":"...",'
                    '"arguments":{...},"reason":"..."}. '
                    "Search the knowledge base before making factual recommendations. "
                    "When you have document IDs, use summarize_document, "
                    "extract_action_items, or compare_incidents as needed. "
                    "Use suggest_debugging_steps for service/symptom checklists. "
                    f"Available tools:\n{tools_json}"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Objective: {objective}\n"
                    f"Parsed hints: {json.dumps(parsed_objective)}\n"
                    f"Step: {step} of {MAX_AGENT_STEPS}\n"
                    f"Prior observations:\n{observations_json}"
                ),
            },
        ]

        raw = complete_agent_step(
            messages=messages,
            completion_provider=self._completion_provider,
            usage_service=self._usage_service,
            workspace_id=context.workspace_id,
            user_id=context.user_id,
            agent_run_id=agent_run_id,
            purpose="agent_planning",
            response_format={"type": "json_object"},
        )
        payload = parse_json_content(raw)
        try:
            return AgentPlanAction.model_validate(payload)
        except Exception as exc:
            raise AgentCompletionError("Agent returned invalid planning payload") from exc

    def _generate_summary(
        self,
        *,
        context: WorkspaceContext,
        agent_run_id: UUID,
        objective: str,
        observations: list[dict[str, Any]],
        citations: list[CitationResponse],
        max_steps_reached: bool,
    ) -> InvestigationSummary:
        if not citations:
            logger.info(
                "agent_insufficient_context_summary",
                agent_run_id=str(agent_run_id),
                workspace_id=str(context.workspace_id),
            )
            return build_insufficient_context_summary(objective)

        allowed_document_ids = {citation.document_id for citation in citations}
        citation_payload = [
            {
                "chunk_id": str(citation.chunk_id),
                "document_id": str(citation.document_id),
                "document_title": citation.document_title,
                "chunk_preview": citation.chunk_preview,
                "score": citation.score,
            }
            for citation in citations
        ]
        messages = [
            {
                "role": "system",
                "content": (
                    "Produce a structured incident investigation summary as JSON with keys: "
                    "problem_statement, summary, likely_causes, likely_related_systems, "
                    "recommended_checks, related_documents (UUID strings), action_items, "
                    "risks_or_unknowns, next_steps. Ground factual claims in provided "
                    "citations only. related_documents must only include document IDs from "
                    "the provided citations."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "objective": objective,
                        "observations": observations,
                        "citations": citation_payload,
                        "max_steps_reached": max_steps_reached,
                    },
                    indent=2,
                ),
            },
        ]

        raw = complete_agent_step(
            messages=messages,
            completion_provider=self._completion_provider,
            usage_service=self._usage_service,
            workspace_id=context.workspace_id,
            user_id=context.user_id,
            agent_run_id=agent_run_id,
            purpose="agent_summary",
            response_format={"type": "json_object"},
        )
        payload = parse_json_content(raw)
        return InvestigationSummary(
            problem_statement=str(payload.get("problem_statement") or objective),
            summary=str(payload.get("summary") or objective),
            likely_causes=[str(item) for item in payload.get("likely_causes") or []],
            likely_related_systems=[
                str(item) for item in payload.get("likely_related_systems") or []
            ],
            recommended_checks=[
                str(item) for item in payload.get("recommended_checks") or []
            ],
            related_documents=_filter_related_documents(
                payload.get("related_documents") or [],
                allowed_document_ids=allowed_document_ids,
            ),
            action_items=[str(item) for item in payload.get("action_items") or []],
            risks_or_unknowns=[
                str(item) for item in payload.get("risks_or_unknowns") or []
            ],
            next_steps=[str(item) for item in payload.get("next_steps") or []],
        )


def _filter_related_documents(
    related_documents: list[Any],
    *,
    allowed_document_ids: set[UUID],
) -> list[UUID]:
    """Keep only unique document IDs present in grounded citations."""
    normalized_docs: list[UUID] = []
    for item in related_documents:
        try:
            doc_id = UUID(str(item))
        except ValueError:
            continue
        if doc_id in allowed_document_ids and doc_id not in normalized_docs:
            normalized_docs.append(doc_id)
    return normalized_docs
