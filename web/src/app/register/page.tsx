"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";

import { useAuth } from "@/components/auth-provider";
import { register } from "@/lib/api/auth";
import { formatAuthError } from "@/lib/auth/errors";
import { resolvePostAuthPath } from "@/lib/auth/post-auth";

function RegisterForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { establishSession } = useAuth();
  const nextPath = resolvePostAuthPath(searchParams.get("next"));

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) {
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const response = await register({
        email: email.trim(),
        password,
      });
      await establishSession(response.access_token, response.user);
      router.replace(nextPath);
      router.refresh();
    } catch (err) {
      setError(formatAuthError(err, "Unable to create your account."));
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
          AtlasOps AI
        </p>
        <p className="mt-2 text-[var(--muted)]">
          Create an account to start a workspace knowledge base.
        </p>

        <form
          onSubmit={(event) => void onSubmit(event)}
          className="mt-8 space-y-4 border-t border-[var(--border)] pt-6"
          noValidate
        >
          <div>
            <label
              htmlFor="register-email"
              className="block text-sm font-medium text-[var(--ink)]"
            >
              Email
            </label>
            <input
              id="register-email"
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
              htmlFor="register-password"
              className="block text-sm font-medium text-[var(--ink)]"
            >
              Password
            </label>
            <input
              id="register-password"
              name="password"
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="mt-1.5 w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--ink)] outline-none focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]"
            />
            <p className="mt-1 text-xs text-[var(--muted)]">
              At least 8 characters.
            </p>
          </div>

          <div>
            <label
              htmlFor="register-confirm-password"
              className="block text-sm font-medium text-[var(--ink)]"
            >
              Confirm password
            </label>
            <input
              id="register-confirm-password"
              name="confirmPassword"
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
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
            {submitting ? "Creating account…" : "Create account"}
          </button>
        </form>

        <p className="mt-6 text-sm text-[var(--muted)]">
          Already have an account?{" "}
          <Link
            href="/login"
            className="font-medium text-[var(--accent)] underline underline-offset-2"
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}

export default function RegisterPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center text-sm text-[var(--muted)]">
          Loading…
        </div>
      }
    >
      <RegisterForm />
    </Suspense>
  );
}
