# API Design

REST API for AtlasOps AI MVP. Base URL: `/api/v1`. All workspace-scoped routes require `Authorization: Bearer <jwt>` and valid workspace membership.

## Common Conventions

### Error Response

```json
{
  "error": {
    "code": "forbidden",
    "message": "You do not have permission to perform this action",
    "details": {}
  }
}
```

HTTP status: `400`, `401`, `403`, `404`, `409`, `422`, `429`, `500`.

### Request ID

Client may send `X-Request-ID`; server generates UUID if absent. Returned in response header and logs.

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
| **Purpose** | Invalidate session (blocklist if enabled) |
| **Role** | Authenticated |
| **Response** | `204 No Content` |
| **Notes** | Client must discard token |

### `GET /auth/me`

| | |
|--|--|
| **Purpose** | Current user profile |
| **Role** | Authenticated |
| **Response 200** | `{ "id", "email", "name", "created_at" }` |
| **Errors** | `401` |

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
| **Query** | `status`, pagination |
| **Response 200** | Jobs with document title, error_message, attempt_count |

### `GET /workspaces/{workspace_id}/admin/audit-logs`

| | |
|--|--|
| **Purpose** | Query audit trail |
| **Query** | `event_type`, `from`, `to`, pagination |
| **Response 200** | Paginated audit events |

### Additional admin aggregates (ADMIN stories)

- `GET .../admin/documents-overview` — counts by status
- `GET .../admin/recent-questions` — last N user messages from RAG
- `GET .../admin/failed-jobs` — shortcut filter `status=failed`

---

## Health & Metrics (Public / Internal)

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | `{ "status": "ok", "db": "ok", "redis": "ok", "worker": "ok" }` |
| `GET /metrics` | Prometheus text format (basic counters/histograms) |

OpenAPI: auto-generated at `/docs` (INFRA-008).
