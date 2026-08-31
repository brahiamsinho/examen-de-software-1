# Handoff — Latest

## What's done

- Full top-level layout created: `backend/`, `frontend/`, `mobile/`,
  `docs/ai/`, root `docker-compose.yml`, root `env.example`, `.gitignore`,
  `README.md`.
- Backend: hand-written Django 5 project (`config` settings package),
  empty `apps/` package, `django-environ`-based settings (DB, CORS,
  ALLOWED_HOSTS, SECRET_KEY, DEBUG all from env vars), DRF + CORS
  installed, `requirements/{base,dev,prod}.txt`, `entrypoint.sh`
  (wait-for-postgres + migrate + exec), multi-stage `Dockerfile`
  (`base`/`dev`/`prod`), `.dockerignore`, `backend/env.example`.
- Frontend: scaffolded via `create-next-app@latest` (TypeScript, ESLint,
  App Router, `src/` dir, no Tailwind, npm, no Turbopack flag — landed on
  Next.js 16.3.3 / React 19.2.8). Added `src/lib/env.ts` (throws at import
  if `NEXT_PUBLIC_API_URL` missing) and `src/lib/api.ts` (fetch wrapper
  using it). `next.config.ts` sets `output: "standalone"`. Multi-stage
  `Dockerfile` (`deps`/`dev`/`build`/`prod`), `.dockerignore`,
  `frontend/env.local.example`. The nested `.git` that `create-next-app`
  auto-initializes was removed so the repo root stays un-initialized.
- Mobile: scaffolded via `flutter create --org com.examen.software
  --project-name mobile mobile`. Added
  `lib/core/config/app_config.dart` reading `API_BASE_URL` via
  `String.fromEnvironment` (default `http://10.0.2.2:8000`). Rest of the
  default counter-app template left untouched. Not dockerized, no
  `mobile` service in compose, per spec.
- `docker-compose.yml`: `db` (postgres:16-alpine + healthcheck), `backend`
  (target `dev`, bind mount, `env_file: ./backend/.env`, depends on
  healthy db), `frontend` (target `dev`, bind mount + anonymous
  `node_modules` volume, `env_file: ./frontend/.env.local`, depends on
  backend). No `mobile` service.
- `docs/ai/*` written with real, specific content (this set of files).

## What's not done

- No git repository initialized anywhere (deliberate, per instructions).
- No `docker compose up`/build was ever run — the compose file and
  Dockerfiles are untested against a live Docker daemon.
- No business Django app, no DRF serializers/viewsets, no real
  frontend UI, no real Flutter screens, no auth — none were in scope.
- Env-example files at every level had to be written as `env.example`
  (no leading dot) instead of `.env.example`, because of a sandbox
  restriction — see `DECISIONS_LOG.md`. They need to be manually renamed
  before `docker compose up` will pick them up as intended.

## How to resume

1. Rename every `env.example`/`env.local.example` to its dotfile form
   (`.env`, `.env.local`) per the root `README.md` quickstart, filling in
   real values.
2. Run `docker compose up --build` and verify all three services come up
   and the frontend can reach the backend (once an API route exists to
   test against — there are none yet beyond `/admin/`).
3. See `docs/ai/NEXT_STEPS.md` for what to build next.
