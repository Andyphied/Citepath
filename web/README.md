# AtlasOps AI — Web App

Minimal Next.js (App Router) demo UI scaffold (**UI-001**).

## Stack

- Next.js 15 (App Router)
- TypeScript
- Tailwind CSS v4
- npm (`package-lock.json`)

## Setup

```bash
cp .env.example .env.local
npm install
npm run dev
```

Open http://localhost:3000

| Variable | Purpose | Default |
|----------|---------|---------|
| `NEXT_PUBLIC_API_URL` | AtlasOps API base URL | `http://localhost:8000` |

The API must allow the web origin (development defaults to `http://localhost:3000` via `CORS_ORIGINS` / `ENVIRONMENT=development`).

## Docker Compose

From the repo root:

```bash
docker compose up --build
```

Web: http://localhost:3000 · API: http://localhost:8000

## Auth (scaffold)

Protected routes redirect to `/login` when the `atlasops_token` cookie is missing. Full login/register is **UI-002**. Until then, the login page accepts a pasted JWT from `POST /auth/login`.

## Workspace context

The header workspace switcher loads `GET /workspaces`, persists the active workspace id in `localStorage`, and exposes `workspacePath(...)` so later pages call `/workspaces/{id}/...` (WS-006).

## Scripts

```bash
npm run dev      # local development
npm run build    # production build
npm run start    # serve production build
npm test         # vitest unit/smoke tests
npm run lint     # eslint
```

## Routes

| Path | Status |
|------|--------|
| `/` | Home + workspace context |
| `/login` | Auth redirect target (stub) |
| `/documents` | Stub → UI-003 |
| `/ask` | Stub → UI-004 |
| `/agent` | Stub → UI-005 |
| `/admin` | Stub → UI-006 (nav gated to owner/admin) |
