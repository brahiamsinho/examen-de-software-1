# Handoff — Latest

## What's done

### SDD Cycle 1: Canonical UML Model, Project Document, Validation Engine (ARCHIVED 2026-09-05)

- **Canonical UML Model (`uml-domain-model`)**: `CanonicalUmlModel` frozen dataclass (alias `UmlModel`) with classes, enumerations, relationships, generation metadata. Supports 8 primitive types (String, Text, Integer, Long, Decimal, Boolean, Date, DateTime) and enumeration references (by id, not name, to survive renames). Multiplicity structured as `(lower: int, upper: int|None)` with parse/format round-trip for UML string syntax.
- **Project Document (`project-document`)**: `ProjectDocument` envelope wrapping `CanonicalUmlModel`, split into semantic `UmlModel` + visual `DiagramLayout`. Includes UUID identity, opaque `owner_id` (non-empty), revision (increments by 1 per mutation), timestamps. No ORM/persistence this cycle.
- **Validation Engine (`uml-validation`)**: Single `validate(model) -> ValidationResult` entry point collecting exhaustive diagnostics. 10 fixed-severity rules (8 ERROR, 2 WARNING). ERROR blocks persistence/generation; WARNING never blocks. Diagnostics carry severity, SCREAMING_SNAKE code, message, slash-rooted id-based path, element reference.
- **Backend**: New Django app `backend/apps/uml_modeling/` with pure Python domain layer (no Django/Ninja/Pydantic imports). One INSTALLED_APPS entry. DB-free, no models/migrations/endpoints. All 23 tasks complete (8 phases, strict TDD). 81 tests pass (80 uml_modeling + 1 pre-existing).
- **Specs**: Three new capability specs moved to `openspec/specs/` as canonical source of truth: `uml-domain-model/spec.md`, `project-document/spec.md`, `uml-validation/spec.md`.
- **Change archived**: `openspec/changes/archive/2026-09-05-canonical-uml-model/` contains proposal, design, tasks, verify-report, and delta specs.
- `docs/ai/` real-state convention updated: `CURRENT_STATE.md`, `ARCHITECTURE.md`, `NEXT_STEPS.md`, `DECISIONS_LOG.md` reflect Cycle-1 completion with 8 proposal decisions (D0-D8) and 9 design decisions (DD1-DD9).

### Prior infrastructure (infra scaffold — Sept 5, commit 9be999a)

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
- No HTTP/WS API endpoints; Ninja/Pydantic schema adapters deferred.
- No persistence (Django ORM, migrations); `revision` field exists but concurrency enforcement is tech debt (item 6).
- No Canvas/Cytoscape.js, Command Bus, Undo/Redo, Auth, Realtime/Channels, Relational mapping, Generators, OpenAPI, Assistant, STT, XMI, Vision (items 4-26, beyond Cycle 1 scope).
- No Flutter screens beyond scaffold; mobile generation not yet implemented.
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
