# Root environment consolidation

## Goal
Use one untracked `.env` file at the repository root for both local development and VM production deployment.

## Tasks
- [x] Create one root `env.example` containing the documented local and production variables.
- [x] Update development and production Compose files to read the root `.env`.
- [x] Remove obsolete distributed environment templates and update deployment instructions.
- [x] Run proportional Compose configuration checks and update project handoff files.

## Evidence
- Root `.env` is ignored and is the sole real configuration file; root `env.example` is the committed template.
- Dev Compose injects root `.env` into backend and frontend. Production Compose interpolates root `.env`, with explicit service environments so secrets are not broadly injected into Caddy/frontend.
- Deleted obsolete templates: `backend/env.example`, `frontend/env.local.example`, `runner/env.example`, `deploy/env.prod.example`.
- VM command: `docker compose -f docker-compose.prod.yml up -d --build`; never use `docker compose down` in instructions.
- Passed: `docker compose --env-file env.example -f docker-compose.yml config -q`.
- Production initially rejected intentionally blank `RUNNER_TOKEN`; passed with temporary shell-only `RUNNER_TOKEN=config-check` for `docker compose --env-file env.example -f docker-compose.prod.yml config -q`.
- No Compose services were started, stopped, or removed.
- Branch: `chore/unify-root-env`
- Commit: pending user approval
