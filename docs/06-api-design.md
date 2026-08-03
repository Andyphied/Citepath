# API Design

REST API for AtlasOps AI MVP. Base URL: `/api/v1`. All workspace-scoped routes require `Authorization: Bearer <jwt>` and valid workspace membership.

## Common Conventions

### Error Response

```json
{
  "error": {
    "code": "forbidden",
    "message": "You do not have permission to perform this action",
    "details": {},
    "request_id": "uuid"
  }
}
```

HTTP status: `400`, `401`, `403`, `404`, `409`, `422`, `429`, `500`.

Auth-related codes: `invalid_credentials`, `token_expired`, `token_invalid`, `unauthorized` (plus `duplicate_email`, `validation_error`, `rate_limited` on auth routes). Schema owner: OBS-004 shared `error_response()`.

### Request ID

Client may send `X-Request-ID`; server generates UUID if absent. Returned in response header, error JSON `request_id`, and logs.

### Pagination

List endpoints: `?page=1&page_size=20` (max 100). Response includes `items`, `total`, `page`, `page_size`.

### Workspace Isolation

Every `{workspace_id}` route validates membership before handler execution. Resource IDs must belong to that workspace or return `404` (not `403`) to avoid enumeration.

---

## Auth

### `POST /auth/register`

| | |
|--|--|
| **Purpose** | Create account and issue JWT |
| **Role** | Public |
| **Request** | `{ "email": "user@example.com", "password": "secret123", "name": "Jane" }` |
| **Response 201** | `{ "user": { "id", "email", "name", "created_at" }, "access_token": "...", "token_type": "bearer", "expires_in": 3600 }` |
| **Errors** | `409` duplicate email, `422` validation |
| **Idempotency** | None; duplicate email is conflict |

### `POST /auth/login`

| | |
|--|--|
| **Purpose** | Authenticate and issue JWT |
| **Role** | Public |
| **Request** | `{ "email", "password" }` |
| **Response 200** | Same token shape as register |
| **Errors** | `401 invalid_credentials` (generic message) |
| **Rate limit** | 10/min per IP |

### `POST /auth/logout`

| | |
|--|--|
| **Purpose** | Acknowledge logout for an authenticated session |
| **Role** | Authenticated |
| **Response** | `204 No Content` |
| **Notes** | MVP has **no Redis JWT blocklist**. The API confirms logout after validating the Bearer token; the **client must discard the JWT**. Subsequent requests with the same token remain valid until expiry unless a future blocklist is added. |

### `GET /auth/me`

| | |
|--|--|
| **Purpose** | Current user profile |
| **Role** | Authenticated |
| **Response 200** | `{ "id", "email", "name", "created_at" }` |
| **Errors** | `401 unauthorized`, `401 token_expired`, `401 token_invalid` |

---

## Workspaces

### `POST /workspaces`

| | |
|--|--|
| **Purpose** | Create workspace; creator becomes Owner |
| **Role** | Authenticated |
| **Request** | `{ "name": "Platform Team", "slug": "platform-team" }` — `slug` optional; auto-generated from `name` when omitted |
| **Response 201** | `{ "id", "name", "slug", "created_at" }` |
| **Errors** | `401 unauthorized`, `409 duplicate_slug`, `422 invalid_slug` |

### `GET /workspaces`

| | |
|--|--|
| **Purpose** | List workspaces for current user |
| **Role** | Authenticated |
| **Response 200** | `{ "items": [{ "id", "name", "role", "created_at" }] }` |
| **Errors** | `401 unauthorized` |

### `GET /workspaces/{workspace_id}`

| | |
|--|--|
| **Purpose** | Workspace detail |
| **Role** | Member+ |
| **Response 200** | `{ "id", "name", "member_count", "created_at" }` |
| **Errors** | `401 unauthorized`, `403 forbidden` if not a member |

### `POST /workspaces/{workspace_id}/members`

| | |
|--|--|
| **Purpose** | Add member by email |
| **Role** | Owner, Admin |
| **Request** | `{ "email": "eng@example.com", "role": "member" }` |
| **Response 201** | `{ "user_id", "email", "role", "created_at" }` |
| **Errors** | `404` user not found, `409` already member |

### `PATCH /workspaces/{workspace_id}/members/{user_id}`

| | |
|--|--|
| **Purpose** | Change member role |
| **Role** | Owner (assign owner), Admin (non-owner roles only) |
| **Request** | `{ "role": "viewer" }` |
| **Response 200** | Updated member |
| **Errors** | `403` last owner demotion, `403` admin assigning owner |
| **Audit** | `role_change` event |

### `DELETE /workspaces/{workspace_id}/members/{user_id}`

| | |
|--|--|
| **Purpose** | Remove member |
| **Role** | Owner, Admin (cannot remove owner unless self) |
| **Response** | `204` |
| **Errors** | `403` last owner removal |

---

## Documents

### `POST /workspaces/{workspace_id}/documents`

| | |
|--|--|
| **Purpose** | Upload document and start ingestion |
| **Role** | Owner, Admin, Member |
| **Request** | `multipart/form-data`: `file`, optional `title`, `source_type` |
| **Response 202** | `{ "document": { "id", "title", "status": "uploaded", "status_label": "Uploaded", ... }, "ingestion_job": { "id", "status": "pending" } }` |
| **Errors** | `403` viewer, `422` invalid file type/size |
| **Audit** | `document_upload` |
| **Idempotency** | Optional header `Idempotency-Key` — same key within 24h returns same document if upload in progress |

### `GET /workspaces/{workspace_id}/documents`

| | |
|--|--|
| **Purpose** | List documents |
| **Role** | All members |
| **Query** | `status`, `source_type`, pagination |
| **Response 200** | Paginated document list with `status` and `status_label` per item |

### `GET /workspaces/{workspace_id}/documents/{document_id}`

| | |
|--|--|
| **Purpose** | Document detail + latest ingestion job |
| **Role** | All members |
| **Response 200** | Document (`status`, `status_label`) + `latest_job`, chunk count if indexed |
| **Errors** | `404` wrong workspace |

### `DELETE /workspaces/{workspace_id}/documents/{document_id}`

| | |
|--|--|
| **Purpose** | Delete document, chunks, storage file |
| **Role** | Owner, Admin, Member |
| **Response** | `204` |
| **Audit** | `document_delete` |

### `POST /workspaces/{workspace_id}/documents/{document_id}/reindex`

| | |
|--|--|
| **Purpose** | Re-run ingestion pipeline |
| **Role** | Owner, Admin, Member |
| **Response 202** | `{ "ingestion_job": { "id", "status": "pending" } }` |
| **Audit** | `reindex` |

---

## Queries / RAG

### `POST /workspaces/{workspace_id}/query`

| | |
|--|--|
| **Purpose** | Ask question; RAG answer with citations |
| **Role** | All members (including Viewer) |
| **Request** | `{ "question": "...", "conversation_id": "uuid|null", "filters": { "source_type": "runbook" } }` |
| **Response 200** | See below |
| **Workspace isolation** | Retrieval limited to workspace chunks |

**Response body:**

```json
{
  "conversation_id": "uuid",
  "message_id": "uuid",
  "answer": "string",
  "confidence": "high|medium|low",
  "citations": [
    {
      "chunk_id": "uuid",
      "document_id": "uuid",
      "document_title": "Billing Runbook",
      "chunk_preview": "First 200 chars...",
      "score": 0.89,
      "metadata": { "page_number": 3 }
    }
  ],
  "suggested_followups": ["..."],
  "insufficient_context": false
}
```

When insufficient context: `insufficient_context: true`, `confidence: "low"`, empty/minimal citations, safe refusal message.

### `GET /workspaces/{workspace_id}/conversations`

| | |
|--|--|
| **Purpose** | List user's conversations in workspace |
| **Role** | All members |
| **Response 200** | Paginated `{ id, title, mode, created_at, updated_at }` |

### `GET /workspaces/{workspace_id}/conversations/{conversation_id}`

| | |
|--|--|
| **Purpose** | Conversation with messages |
| **Role** | Member who owns conversation OR Admin/Owner (MVP: creator only) |
| **Response 200** | `{ conversation, messages: [{ role, content, metadata, created_at }] }` |

---

## Agent Runs

### `POST /workspaces/{workspace_id}/agent-runs`

| | |
|--|--|
| **Purpose** | Start incident investigation |
| **Role** | All members (including Viewer) |
| **Request** | `{ "objective": "Billing API returning 502 after deploy...", "conversation_id": null }` |
| **Response 200** | Structured result (sync; may take up to 120s) |

**Response body:**

```json
{
  "agent_run_id": "uuid",
  "status": "completed",
  "summary": {
    "problem_statement": "...",
    "likely_causes": ["..."],
    "recommended_checks": ["..."],
    "related_documents": ["uuid"],
    "action_items": ["..."]
  },
  "citations": [ /* same shape as RAG */ ],
  "tool_calls_count": 4
}
```

### `GET /workspaces/{workspace_id}/agent-runs/{agent_run_id}`

| | |
|--|--|
| **Purpose** | Get agent run status and result |
| **Role** | Run creator or Admin/Owner |
| **Response 200** | Full run record |

### `GET /workspaces/{workspace_id}/agent-runs/{agent_run_id}/tool-calls`

| | |
|--|--|
| **Purpose** | List tool calls for audit/debug |
| **Role** | Admin, Owner (Member: own runs only) |
| **Response 200** | `{ "items": [{ tool_name, input, output, status, latency_ms, created_at }] }` |

---

## Admin

All admin routes: **Owner, Admin only**.

### `GET /workspaces/{workspace_id}/admin/usage`

| | |
|--|--|
| **Purpose** | Usage summary for dashboard |
| **Query** | `from`, `to` (ISO-8601 datetimes; window is `[from, to)`, default last 7 days ending now UTC) |
| **Response 200** | `{ "workspace_id", "from", "to", "totals": { "prompt_tokens", "completion_tokens", "embedding_tokens", "estimated_cost_usd", "call_count" }, "by_day": [{ "date", ... }], "by_operation": [{ "operation", ... }] }` |
| **Errors** | Viewer/Member → `403`; invalid range → `422 invalid_usage_range` |

### `GET /workspaces/{workspace_id}/admin/ingestion-jobs`

| | |
|--|--|
| **Purpose** | List ingestion jobs with failures highlighted |
| **Query** | `status` (`pending`/`processing`/`completed`/`failed`), `page`, `page_size` (max 100) |
| **Response 200** | `{ "items": [{ "id", "workspace_id", "document_id", "document_title", "status", "attempt_count", "error_message", "started_at", "completed_at", "created_at" }], "total", "page", "page_size" }` |
| **Errors** | Viewer/Member → `403` |

### `GET /workspaces/{workspace_id}/admin/documents-overview`

| | |
|--|--|
| **Purpose** | Corpus health: totals, counts by status, recent uploads |
| **Role** | Owner, Admin (`VIEW_ADMIN_DASHBOARD`) |
| **Response 200** | `{ "workspace_id", "total", "by_status": { "uploaded", "processing", "indexed", "failed" }, "recent_uploads": [{ "id", "title", "status", "status_label", "uploaded_by", "created_at" }] }` |
| **Errors** | Viewer/Member → `403` |

### `GET /workspaces/{workspace_id}/admin/recent-questions`

| | |
|--|--|
| **Purpose** | Recent user RAG questions (preview only; no assistant/system prompts) |
| **Query** | `page`, `page_size` (default 50, max 100) |
| **Response 200** | `{ "items": [{ "message_id", "conversation_id", "user_id", "user_name", "user_email", "question_preview", "created_at" }], "total", "page", "page_size" }` |
| **Errors** | Viewer/Member → `403` |

### `GET /workspaces/{workspace_id}/admin/failed-jobs`

| | |
|--|--|
| **Purpose** | Dashboard widget: failed job counts (24h / 7d) + recent failures |
| **Response 200** | `{ "failed_last_24h", "failed_last_7d", "items": […ingestion job shape…], "empty_message" }` (`empty_message` is `"No failed jobs."` when `failed_last_7d` is 0) |
| **Notes** | Full filtered list: `GET .../admin/ingestion-jobs?status=failed` |
| **Errors** | Viewer/Member → `403` |

### `GET /workspaces/{workspace_id}/admin/audit-logs`

| | |
|--|--|
| **Purpose** | Query append-only audit trail (newest first) |
| **Role** | Owner, Admin (`VIEW_ADMIN_DASHBOARD`) |
| **Query** | `event_type`, `actor_user_id`, `from`, `to` (ISO-8601; window is `[from, to)`), `page`, `page_size` (max 100) |
| **Response 200** | `{ "items": [{ "id", "workspace_id", "actor_user_id", "event_type", "metadata", "ip_address", "created_at" }], "total", "page", "page_size" }` |
| **Errors** | Viewer/Member → `403`; inverted `from`/`to` → `422 invalid_audit_range` |
| **Notes** | No delete/update API; workspace-scoped only |

### Admin aggregates (ADMIN stories)

| Endpoint | Story | Notes |
|----------|-------|-------|
| `GET .../admin/documents-overview` | ADMIN-001 | Counts by status + recent uploads |
| `GET .../admin/ingestion-jobs` | ADMIN-002 / OBS-007 | Status filter; document title join; `pending_count` |
| `GET .../admin/recent-questions` | ADMIN-003 | Default page size 50 |
| `GET .../admin/usage` | ADMIN-004 / USAGE-004 | 7-day totals + estimated cost (no duplicate endpoint) |
| `GET .../admin/failed-jobs` | ADMIN-005 | 24h/7d counts; link clients to `?status=failed` |

---

## Health & Metrics (Public / Internal)

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Liveness: `{ "status": "ok" }` |
| `GET /health/ready` | Readiness: `{ "status", "database", "redis", "queue_depth", "worker": { "status", "queue_depth" } }`. `worker.status` = Redis queue probe ok/error (not Celery process liveness). On probe failure `queue_depth` is coerced to `0` with `worker.status=error`. |
| `GET /metrics` | Prometheus text format (counters + ingestion duration histogram; unauthenticated — restrict at network edge) |

OpenAPI: auto-generated at `/docs` (INFRA-008).
