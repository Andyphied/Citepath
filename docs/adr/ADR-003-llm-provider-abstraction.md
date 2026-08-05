# ADR-003: LLM Provider Abstraction

## Status

Accepted

## Context

MVP assumes one active LLM provider at a time (OpenAI or Anthropic, assumption A2) but the PRD mentions both for portfolio credibility. Hard-coding OpenAI calls in RAG and agent modules would complicate testing, provider switching, and cost tracking normalization.

## Decision

Introduce provider interfaces in `infrastructure/llm/`:

- `ChatCompletionProvider.complete(messages, tools?, response_format?) → CompletionResult`
- `EmbeddingProvider.embed(texts: list[str]) → list[vector]`

Concrete implementations: `OpenAIProvider`, `AnthropicProvider`, `OpenAIEmbeddingProvider`. Select via `LLM_PROVIDER` environment variable. Domain modules (`rag`, `agents`, `retrieval`) depend only on interfaces injected at startup.

LangChain is **optional** — not required; direct SDK calls behind interfaces are sufficient for MVP.

## Consequences

**Positive:**
- Domain logic free of vendor-specific request shapes
- Unit tests mock interfaces without network
- Unified `CompletionResult` enables consistent usage logging (tokens, latency, model)
- Switching providers is configuration, not refactor

**Negative:**
- Thin abstraction layer adds initial boilerplate
- Lowest-common-denominator tool-calling schema mapping between OpenAI and Anthropic
- Two provider implementations to smoke-test (mitigate: CI mocks one; manual test other)

## Alternatives Considered

| Alternative | Why not selected |
|-------------|------------------|
| **OpenAI only, no abstraction** | Faster day one but contradicts PRD flexibility and complicates testing |
| **LangChain everywhere** | Heavy dependency; obscures control flow for agent loop and citation mapping |
| **LiteLLM proxy** | Extra runtime component; overkill for MVP monolith |

## Implementation Notes

- `CompletionResult` fields: `content`, `tool_calls`, `prompt_tokens`, `completion_tokens`, `model`, `latency_ms`, `raw_response` (debug only, not logged)
- Map Anthropic tool_use blocks to internal `ToolCall` dataclass same as OpenAI
- Embedding provider independent from chat provider (embeddings stay OpenAI for MVP even if chat is Anthropic)
- Never import `openai` or `anthropic` outside `infrastructure/llm/`
- Log all calls through `UsageService` regardless of provider
