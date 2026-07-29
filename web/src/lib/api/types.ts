/** Shared API response types aligned with AtlasOps backend schemas. */

export type WorkspaceRole = "owner" | "admin" | "member" | "viewer";

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}

export interface User {
  id: string;
  email: string;
  name: string | null;
  created_at: string;
}

export interface AuthTokenResponse {
  user: User;
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface WorkspaceListItem {
  id: string;
  name: string;
  role: WorkspaceRole | string;
  created_at: string;
}

export interface WorkspaceListResponse {
  items: WorkspaceListItem[];
}

export function isAdminRole(role: string | undefined | null): boolean {
  return role === "owner" || role === "admin";
}

/** Owner / admin / member may upload; viewer is list-only (DOC-001 / WS-005). */
export function canUploadDocuments(role: string | undefined | null): boolean {
  return role === "owner" || role === "admin" || role === "member";
}

export type DocumentStatusValue =
  | "uploaded"
  | "processing"
  | "indexed"
  | "failed"
  | string;

export interface DocumentItem {
  id: string;
  workspace_id: string;
  title: string;
  source_type: string | null;
  file_type: string;
  status: DocumentStatusValue;
  status_label: string;
  uploaded_by: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  items: DocumentItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface DocumentUploadResponse {
  document: DocumentItem;
  ingestion_job: {
    id: string;
    status: string;
  };
}

export type ConfidenceLevel = "high" | "medium" | "low" | string;

export interface CitationItem {
  chunk_id: string;
  document_id: string;
  document_title: string | null;
  chunk_preview: string;
  score: number;
  metadata?: Record<string, unknown> | null;
}

export interface QueryRequest {
  question: string;
  conversation_id?: string | null;
}

export interface QueryResponse {
  conversation_id: string;
  message_id: string;
  answer: string;
  confidence: ConfidenceLevel;
  citations: CitationItem[];
  suggested_followups: string[];
  insufficient_context: boolean;
}

/** AGENT-008 structured investigation result (InvestigationSummary). */
export interface InvestigationSummary {
  problem_statement: string;
  summary: string;
  likely_causes: string[];
  likely_related_systems: string[];
  recommended_checks: string[];
  related_documents: string[];
  action_items: string[];
  risks_or_unknowns: string[];
  next_steps: string[];
}

export interface AgentRunRequest {
  objective: string;
  conversation_id?: string | null;
}

export interface AgentRunResponse {
  agent_run_id: string;
  status: string;
  summary: InvestigationSummary | null;
  citations: CitationItem[];
  tool_calls_count: number;
}
