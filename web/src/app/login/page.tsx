"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { sanitizeNextPath } from "@/lib/auth/safe-next";
import { setAccessToken } from "@/lib/auth/session";

function LoginStubInner() {
  const searchParams = useSearchParams();
  const nextPath = sanitizeNextPath(searchParams.get("next"));
  const [token, setToken] = useState("");
  const [saved, setSaved] = useState(false);

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--canvas)] px-4">
      <div className="w-full max-w-md">
        <p className="font-[family-name:var(--font-display)] text-3xl text-[var(--ink)]">
          AtlasOps AI
        </p>
        <p className="mt-2 text-[var(--muted)]">
          Sign-in UI arrives in UI-002. Protected routes redirect here when no
          session cookie is present.
        </p>

        <div className="mt-8 border-t border-[var(--border)] pt-6">
          <p className="text-sm font-medium text-[var(--ink)]">
            Scaffold helper — paste JWT
          </p>
          <p className="mt-1 text-xs text-[var(--muted)]">
            Temporary until UI-002. Obtain a token via{" "}
            <code className="font-[family-name:var(--font-mono)]">
              POST /auth/login
            </code>
            .
          </p>
          <textarea
            className="mt-3 h-28 w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 py-2 font-[family-name:var(--font-mono)] text-xs text-[var(--ink)] outline-none focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]"
            placeholder="eyJhbGciOiJIUzI1NiIs..."
            value={token}
            onChange={(event) => {
              setToken(event.target.value);
              setSaved(false);
            }}
          />
          <div className="mt-3 flex items-center gap-3">
            <button
              type="button"
              className="rounded-md bg-[var(--accent)] px-3 py-2 text-sm font-medium text-white hover:brightness-110"
              onClick={() => {
                const trimmed = token.trim();
                if (!trimmed) {
                  return;
                }
                setAccessToken(trimmed);
                setSaved(true);
                window.location.href = nextPath;
              }}
            >
              Continue
            </button>
            {saved ? (
              <span className="text-xs text-[var(--accent)]">Session set</span>
            ) : null}
          </div>
        </div>

        <p className="mt-8 text-xs text-[var(--muted)]">
          Returning? Full email/password login is{" "}
          <Link href="/login" className="underline underline-offset-2">
            UI-002
          </Link>
          .
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center text-sm text-[var(--muted)]">
          Loading…
        </div>
      }
    >
      <LoginStubInner />
    </Suspense>
  );
}
