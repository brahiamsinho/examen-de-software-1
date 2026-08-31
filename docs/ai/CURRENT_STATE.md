# Current State

This is the initial scaffold. Nothing beyond infrastructure exists yet:

- **Backend**: empty Django project (`config` settings package), no
  business apps under `backend/apps/` yet. DRF and CORS are installed and
  configured but there are no serializers, viewsets, or models beyond
  Django's own built-in apps (admin, auth, sessions, etc.).
- **Frontend**: default Next.js App Router page (`create-next-app`
  output) plus a small `src/lib/env.ts` / `src/lib/api.ts` helper pair for
  reading the backend URL from `NEXT_PUBLIC_API_URL`. No custom UI yet.
- **Mobile**: default Flutter counter-app template, plus
  `lib/core/config/app_config.dart` reading `API_BASE_URL` via
  `--dart-define`. No real screens yet.
- **Docker Compose**: `db` (Postgres 16), `backend` (Django dev server),
  and `frontend` (Next.js dev server) are wired for local development
  with live reload. Not yet run/tested against a live Docker daemon as
  part of this scaffold (no `docker compose up` was executed).

Nothing has been committed to git yet — the project has no `.git`
directory at the repository root.
