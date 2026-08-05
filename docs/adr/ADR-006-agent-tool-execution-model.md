# ADR-006: Agent Tool Execution Model

## Status

Accepted

## Context

The MVP incident agent must use tools to investigate knowledge bases without performing destructive or external actions (assumption A10). The agent must be auditable, cite sources, and resist prompt injection from document content.

## Decision

Implement a **controlled static tool registry** with explicit executor validation:

1. LLM receives JSON schemas for **allowed tools only** (5 MVP tools)
2. Orchestrator parses tool call request
3. **Executor validates** tool name ∈ registry before dispatch
4. Tools receive `WorkspaceContext` injected by executor — not from LLM args
5. All tools are **read-only** and workspace-scoped
6. Every execution logged to `agent_tool_calls`
7. No dynamic tool registration, no user-defined tools, no external HTTP tools in MVP

Forbidden: shell, file write, delete, deploy, ticket create, arbitrary code execution.

## Consequences

**Positive:**
- Bounded blast radius — worst case is read excess data within workspace user already accesses
- Clear audit trail per tool invocation
- CI can test rejection of unknown tools deterministically
- Aligns with PRD agent rules and portfolio security narrative

**Negative:**
- Agent cannot adapt tools without code deploy
- Single tool per step in MVP simplifies logging but may increase step count
- LLM may request disallowed tools — must handle gracefully

## Alternatives Considered

| Alternative | Why not selected |
|-------------|------------------|
| **Unrestricted function calling** | Violates MVP safety requirements |
| **MCP / external tool servers** | Extra infrastructure and trust boundary |
| **Human approval per tool** | UX friction; defer post-MVP |
| **Hard-coded agent script (no LLM tools)** | Not flexible enough for varied incident objectives |

## Implementation Notes

- Registry in `modules/agents/tool_registry.py` as dict name → `ToolHandler`
- `ToolExecutor.run(name, args, ctx)` validates name, validates args with Pydantic, injects workspace
- Document IDs in args verified: `document.workspace_id == ctx.workspace_id`
- Wrap tool outputs as data blocks in agent message history with delimiter to reduce prompt injection
- Max 8 steps, 120s timeout, 16K token soft cap per run
- Final summary must include citations aggregated from tool outputs
