import { apiFetch } from "@/lib/api/client";
import type {
  DocumentListResponse,
  DocumentUploadResponse,
} from "@/lib/api/types";

export type ListDocumentsParams = {
  page?: number;
  pageSize?: number;
  status?: string;
};

/** GET /workspaces/{id}/documents */
export function listDocuments(
  workspaceId: string,
  params: ListDocumentsParams = {},
): Promise<DocumentListResponse> {
  const query = new URLSearchParams();
  if (params.page != null) {
    query.set("page", String(params.page));
  }
  if (params.pageSize != null) {
    query.set("page_size", String(params.pageSize));
  }
  if (params.status) {
    query.set("status", params.status);
  }
  const qs = query.toString();
  const path = `/workspaces/${workspaceId}/documents${qs ? `?${qs}` : ""}`;
  return apiFetch<DocumentListResponse>(path);
}

/**
 * POST /workspaces/{id}/documents — multipart upload.
 * Field name `file` matches the FastAPI UploadFile parameter.
 */
export function uploadDocument(
  workspaceId: string,
  file: File,
  options: { title?: string; sourceType?: string } = {},
): Promise<DocumentUploadResponse> {
  const body = new FormData();
  body.append("file", file);
  if (options.title) {
    body.append("title", options.title);
  }
  if (options.sourceType) {
    body.append("source_type", options.sourceType);
  }
  return apiFetch<DocumentUploadResponse>(
    `/workspaces/${workspaceId}/documents`,
    {
      method: "POST",
      body,
    },
  );
}
