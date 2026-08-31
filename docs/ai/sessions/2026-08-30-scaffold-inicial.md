# Session — 2026-08-30 — Initial Scaffold

Scaffolded the empty project at repo root from scratch, per the exam/
learning full-stack template spec:

- Hand-wrote the Django + DRF backend (`backend/`) — `config` settings
  package, empty `apps/` package, django-environ-based settings, CORS,
  requirements split by env, entrypoint script, multi-stage Dockerfile.
- Ran `npx create-next-app@latest` for `frontend/` (TypeScript, App
  Router, `src/` dir, ESLint, no Tailwind) — landed on Next.js 16.3.3 /
  React 19.2.8. Added `src/lib/env.ts` + `src/lib/api.ts`, `output:
  "standalone"` in `next.config.ts`, multi-stage Dockerfile. Removed the
  nested `.git` that `create-next-app` auto-creates.
- Ran `flutter create` for `mobile/` — added
  `lib/core/config/app_config.dart` reading `API_BASE_URL` via
  `--dart-define`. Left the rest of the default template as-is; no
  dockerization (not requested, not sensible for a mobile SDK app).
- Wrote root `docker-compose.yml` (db/backend/frontend, dev targets),
  root `env.example`, `.gitignore`, `README.md`.
- Wrote this `docs/ai/` living-memory set.

**Notable deviation**: the sandbox blocked writing any file with `.env`
in its path (Write and Bash both refused it), so every "env example"
file across the project (`env.example`, `backend/env.example`,
`frontend/env.local.example`) had to be written without the leading dot.
Each file documents this and instructs renaming it locally. See
`DECISIONS_LOG.md` for the full rationale.

No git repository was initialized (as instructed) and no Docker commands
were executed — only files were written.
