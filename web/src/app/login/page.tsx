"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";

import { useAuth } from "@/components/auth-provider";
import { login } from "@/lib/api/auth";
import { formatAuthError } from "@/lib/auth/errors";
import { resolvePostAuthPath } from "@/lib/auth/post-auth";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { establishSession } = useAuth();
  const nextPath = resolvePostAuthPath(searchParams.get("next"));

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) {
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const response = await login({
        email: email.trim(),
        password,
      });
      await establishSession(response.access_token, response.user);
      router.replace(nextPath);
      router.refresh();
    } catch (err) {
      setError(formatAuthError(err, "Invalid email or password"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,_#d9f2ef_0%,_transparent_55%),linear-gradient(160deg,_#eef1f4_0%,_#e3e9f0_45%,_#d7e4e2_100%)]"
      />
      <div className="relative w-full max-w-md">
        <p className="font-[family-name:var(--font-display)] text-4xl tracking-tight text-[var(--ink)]">
          Citepath
        </p>
        <p className="mt-2 text-[var(--muted)]">
          Sign in to your workspace knowledge ops console.
        </p>

        <form
          onSubmit={(event) => void onSubmit(event)}
          className="mt-8 space-y-4 border-t border-[var(--border)] pt-6"
          noValidate
        >
          <div>
            <label
              htmlFor="login-email"
              className="block text-sm font-medium text-[var(--ink)]"
            >
              Email
            </label>
            <input
              id="login-email"
              name="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="mt-1.5 w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--ink)] outline-none focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]"
            />
          </div>

          <div>
            <label
              htmlFor="login-password"
              className="block text-sm font-medium text-[var(--ink)]"
            >
              Password
            </label>
            <input
              id="login-password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              minLength={8}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="mt-1.5 w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--ink)] outline-none focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]"
            />
          </div>

          {error ? (
            <p
              role="alert"
              className="rounded-md border border-[var(--danger-border)] bg-[var(--danger-bg)] px-3 py-2 text-sm text-[var(--danger)]"
            >
              {error}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-md bg-[var(--accent)] px-3 py-2.5 text-sm font-medium text-white hover:brightness-110 disabled:opacity-60"
          >
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="mt-6 text-sm text-[var(--muted)]">
          New here?{" "}
          <Link
            href="/register"
            className="font-medium text-[var(--accent)] underline underline-offset-2"
          >
            Create an account
          </Link>
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
      <LoginForm />
    </Suspense>
  );
}
