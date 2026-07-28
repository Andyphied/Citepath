"use client";

import { useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import { DocumentsTable } from "@/components/documents/documents-table";
import { DocumentUploadZone } from "@/components/documents/upload-zone";
import { ErrorState } from "@/components/error-state";
import { FeedbackBanner, type ToastTone } from "@/components/feedback-banner";
import { LoadingState } from "@/components/loading-state";
import { useWorkspace } from "@/components/workspace-provider";
import { ApiError } from "@/lib/api/client";
import { listDocuments, uploadDocument } from "@/lib/api/documents";
import {
  canUploadDocuments,
  type DocumentItem,
} from "@/lib/api/types";
import { anyDocumentInFlight } from "@/lib/documents/status";

const POLL_MS = 2500;
const LIST_PAGE_SIZE = 50;

type Feedback = { tone: ToastTone; message: string };

function errorMessage(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.message : fallback;
}

export default function DocumentsPage() {
  const { user } = useAuth();
  const {
    activeWorkspace,
    activeWorkspaceId,
    loading: workspaceLoading,
    error: workspaceError,
    refresh: refreshWorkspaces,
  } = useWorkspace();

  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [total, setTotal] = useState(0);
  const [listLoading, setListLoading] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [feedback, setFeedback] = useState<Feedback | null>(null);

  const canUpload = canUploadDocuments(activeWorkspace?.role);

  const loadDocuments = useCallback(
    async (opts: { quiet?: boolean } = {}) => {
      if (!activeWorkspaceId) {
        setDocuments([]);
        setTotal(0);
        setListError(null);
        return;
      }

      if (!opts.quiet) {
        setListLoading(true);
      }
      setListError(null);
      try {
        const response = await listDocuments(activeWorkspaceId, {
          page: 1,
          pageSize: LIST_PAGE_SIZE,
        });
        setDocuments(response.items ?? []);
        setTotal(response.total ?? 0);
      } catch (err) {
        setListError(errorMessage(err, "Failed to load documents."));
        if (!opts.quiet) {
          setDocuments([]);
          setTotal(0);
        }
      } finally {
        if (!opts.quiet) {
          setListLoading(false);
        }
      }
    },
    [activeWorkspaceId],
  );

  useEffect(() => {
    if (workspaceLoading) {
      return;
    }
    void loadDocuments();
  }, [workspaceLoading, loadDocuments]);

  useEffect(() => {
    if (!activeWorkspaceId || !anyDocumentInFlight(documents)) {
      return;
    }
    const timer = window.setInterval(() => {
      void loadDocuments({ quiet: true });
    }, POLL_MS);
    return () => window.clearInterval(timer);
  }, [activeWorkspaceId, documents, loadDocuments]);

  useEffect(() => {
    if (!feedback || feedback.tone === "error") {
      return;
    }
    const timer = window.setTimeout(() => setFeedback(null), 4000);
    return () => window.clearTimeout(timer);
  }, [feedback]);

  const handleUpload = useCallback(
    async (file: File) => {
      if (!activeWorkspaceId || !canUpload) {
        return;
      }
      setUploading(true);
      setFeedback({
        tone: "info",
        message: `Uploading ${file.name}…`,
      });
      try {
        const result = await uploadDocument(activeWorkspaceId, file);
        setFeedback({
          tone: "success",
          message: `Uploaded “${result.document.title}” — status ${result.document.status_label}.`,
        });
        await loadDocuments({ quiet: true });
      } catch (err) {
        setFeedback({
          tone: "error",
          message: errorMessage(err, "Upload failed. Try again."),
        });
      } finally {
        setUploading(false);
      }
    },
    [activeWorkspaceId, canUpload, loadDocuments],
  );

  const showEmpty =
    !listLoading && !listError && documents.length === 0 && !!activeWorkspaceId;

  return (
    <AppShell title="Documents">
      <section className="mx-auto flex w-full max-w-5xl flex-col gap-6">
        <div>
          <h2 className="font-[family-name:var(--font-display)] text-2xl text-[var(--ink)]">
            Documents
          </h2>
          <p className="mt-2 text-sm text-[var(--muted)] leading-relaxed">
            Upload runbooks and track ingestion status for the active workspace.
          </p>
        </div>

        {feedback ? (
          <FeedbackBanner
            tone={feedback.tone}
            message={feedback.message}
            onDismiss={() => setFeedback(null)}
          />
        ) : null}

        {workspaceLoading ? (
          <LoadingState label="Loading workspace…" />
        ) : null}

        {workspaceError ? (
          <ErrorState
            title="Workspace error"
            message={workspaceError}
            onRetry={() => {
              void refreshWorkspaces();
            }}
          />
        ) : null}

        {!workspaceLoading && !workspaceError && !activeWorkspaceId ? (
          <p className="text-sm text-[var(--muted)]">
            Select or create a workspace to manage documents.
          </p>
        ) : null}

        {activeWorkspaceId && canUpload ? (
          <DocumentUploadZone
            uploading={uploading}
            onFileSelected={(file) => {
              void handleUpload(file);
            }}
          />
        ) : null}

        {activeWorkspaceId && !canUpload ? (
          <p className="rounded-md border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-sm text-[var(--muted)]">
            You have Viewer access — documents are read-only. Ask an Admin to
            upload runbooks.
          </p>
        ) : null}

        {activeWorkspaceId && listLoading ? (
          <LoadingState label="Loading documents…" />
        ) : null}

        {activeWorkspaceId && listError ? (
          <ErrorState
            title="Could not load documents"
            message={listError}
            onRetry={() => {
              void loadDocuments();
            }}
          />
        ) : null}

        {showEmpty ? (
          <div className="rounded-md border border-[var(--border)] bg-[var(--surface)] px-6 py-10 text-center">
            <p className="font-[family-name:var(--font-display)] text-xl text-[var(--ink)]">
              Upload your first runbook
            </p>
            <p className="mx-auto mt-2 max-w-md text-sm text-[var(--muted)] leading-relaxed">
              {canUpload
                ? "Drop a markdown or PDF file above to start the ingest loop."
                : "No documents in this workspace yet."}
            </p>
          </div>
        ) : null}

        {!listLoading && !listError && documents.length > 0 ? (
          <DocumentsTable
            documents={documents}
            total={total}
            currentUserId={user?.id}
          />
        ) : null}
      </section>
    </AppShell>
  );
}
