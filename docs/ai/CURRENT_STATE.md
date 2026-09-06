# Current State

This is the "real state document" required by `product-04-next-django.md`
section 1 — kept independent of the frozen spec, updated as work actually
lands. Be honest here even when it's unflattering: this file should never
claim more progress than actually exists.

## Where the project actually is

**Nothing from the real UML/CASE-tool domain exists yet.** No
`CanonicalUmlModel`, no canvas, no collaboration, no code generation, no
AI/voice/XMI features have been built. What exists is a dockerized
infrastructure skeleton that is mid-migration from its original generic
scaffold onto the corrected stack, plus SDD tooling that has been
initialized but not yet used for a real cycle.

### Backend

- Dockerized Django project skeleton exists (`config` settings package,
  empty `apps/`).
- **In progress by a parallel workstream**: migration from Django REST
  Framework to Django Ninja, addition of Django Channels + Daphne (ASGI),
  addition of Argon2 password hashing + PyJWT, and bootstrap of
  pytest + pytest-django + hypothesis, including a health-check endpoint
  and one smoke test. This is **not confirmed complete** as of this
  reconciliation — its final result was not available to verify.
- **Postgres is now a hard test prerequisite.** With `backend/apps/users/` and
  `backend/apps/organizations/` landing the project's first migrations, `pytest-django` builds its test
  database from the `POSTGRES_*` env vars on every run — a reachable `db`
  service (`docker compose up -d db backend`) is required before
  `docker compose exec backend pytest` (or `cd backend && pytest`) will
  work. `apps/uml_modeling/` itself stays DB-free and unaffected.

### Frontend

- Dockerized Next.js (App Router, TypeScript) skeleton exists with a
  minimal `env.ts`/`api.ts` pair.
- **In progress by a parallel workstream**: addition of Tailwind CSS +
  shadcn/ui + Cytoscape.js + cytoscape-fcose + Jotai, and bootstrap of
  Vitest + React Testing Library, including one smoke test. This is **not
  confirmed complete** as of this reconciliation — its final result was
  not available to verify.

### Mobile

- `mobile/` is a bare Flutter scaffold (default counter-app template plus
  an `AppConfig` reading `API_BASE_URL`). It does not yet implement
  anything domain-specific for the CASE tool. This is the instructor-
  mandated real Flutter client for the main tool (see `PROJECT_VISION.md`
  and `ARCHITECTURE.md`) — still to be designed and built out.

### End-to-end testing

- Cypress bootstrap is planned but has not been started by anyone yet.

### SDD / planning

- `openspec/` is initialized at the repo root (config + specs + changes
  directories exist). **SDD Cycle 1** (`canonical-uml-model`) has run
  through explore → propose → spec → design → tasks → apply; `sdd-verify`
  and `sdd-archive` are the remaining steps for this change.
- **SDD Cycle 2** (`multi-tenant-identity`) is **fully implemented**
  across its 3 chained PRs (`stacked-to-main`, review-budget guard), and
  was subsequently split from a single `apps/identity/` app into two
  apps per Django's one-app-per-domain convention:
  `backend/apps/users/` (`AUTH_USER_MODEL = "users.User"`, the `User`
  model, `register_user`/`authenticate_user` services, `auth_router`) and
  `backend/apps/organizations/` (`Organization`, `TenantScopedModel`/
  `Membership` models, the tenancy/membership services and
  `_assert_not_last_owner` guard, `permissions.py`
  (`resolve_membership`/`require_role`), `organizations_router`/
  `memberships_router`) — the project's **first migrations** (PR 1);
  services + permissions (PR 2); schemas, routers mounted in
  `config/api.py`, and the DD2 cross-origin session/CSRF settings block
  in `config/settings.py` plus `backend/env.example` (PR 3). 168/168
  backend tests pass. `sdd-verify`/`sdd-archive` are the remaining steps.
  Three deviations from design.md were required and are documented in
  `tasks.md`'s Phase 5 note: (1) the installed django-ninja 1.7 has no
  `NinjaAPI(csrf=True)` kwarg — CSRF is enforced equivalently via
  `django_auth`'s built-in check plus an explicit `check_csrf()` call on
  the two anonymous unsafe endpoints; (2) `org_slug` (a mount-prefix path
  segment) needed an explicit `Path[str]` annotation per operation,
  since this ninja version does not auto-detect prefix-only path params;
  (3) `email-validator` was added as a new, small dependency to support
  `EmailStr` in the schemas — the proposal's "no new dependency" line is
  now inaccurate by that one package.

### Domain

- **SDD Cycle 1 is implemented** (`backend/apps/uml_modeling/`, change
  `canonical-uml-model`): `CanonicalUmlModel` (alias `UmlModel`) with
  classes, enumerations, relationships, and generation metadata;
  `ProjectDocument`/`DiagramLayout` (identity, opaque `owner_id`, pure
  revision increment via `with_model`/`with_layout`); and the single
  validation `engine.validate()` with its full 10-rule Cycle-1 registry
  (`EMPTY_ELEMENT_NAME`, `DUPLICATE_CLASS_NAME`, `DUPLICATE_ATTRIBUTE_NAME`,
  `DUPLICATE_ENUMERATION_LITERAL`, `UNKNOWN_ATTRIBUTE_TYPE`,
  `INVALID_RELATIONSHIP_ENDPOINT`, `INVALID_MULTIPLICITY`,
  `GENERALIZATION_CYCLE`, `SELF_ASSOCIATION`, `CLASS_WITHOUT_ATTRIBUTES`).
  This is a pure, DB-free, framework-agnostic domain layer: no
  `models.py`, no migrations, no urlconf, no Ninja/Pydantic schemas, no
  persistence, and no auth wiring yet — `owner_id` is a validated-opaque
  string only. 80 backend tests cover it (TDD, `pytest` + `hypothesis`),
  with zero regression to the pre-existing health-check smoke test.
- `UmlCommand`/Command Bus, the Cytoscape canvas, persistence (Django
  ORM), realtime collaboration, the relational mapper, the Spring Boot
  generator, the Domain Manifest, the assistant pipeline, and all
  AI/voice/image/XMI features are **not started**.

## Pending (SDD Cycle 1 and beyond)

Per the spec's own recommended implementation order (section 37), the next
work — once explored/proposed via SDD — should proceed roughly in this
order:

1. `CanonicalUmlModel`
2. `ProjectDocument` + `DiagramLayout`
3. Validation engine
4. `UmlCommand` + Command Bus
5. Canvas (Cytoscape.js)
6. Persistence (Django ORM)
7. Undo/Redo
8. Auth + ownership
9. Realtime (Django Channels + Daphne)
10. Presence
11. UML → RelationalModel
12. Spring Boot backend generator
13. Generated backend compilable
14. OpenAPI
15. Postman collection
16. Domain Manifest
17. Frontend generator
18. Generic CRUD (generated apps)
19. `AssistantCommand`
20. Text → command (ONNX Runtime + Optimum)
21. Executor
22. STT (Vosk, Spanish, local)
23. Voice → command
24. Android via Next.js PWA + Capacitor (generated output)
25. XMI 2.1
26. Image → UML (Moondream)

SDD Cycle 1 (see `NEXT_STEPS.md`) targeted items 1–3 only:
`CanonicalUmlModel`, `ProjectDocument`/`DiagramLayout`, and the
validation engine. Implementation (`sdd-apply`) is complete; `sdd-verify`
and `sdd-archive` remain before item 4 (`UmlCommand` + Command Bus)
starts as its own cycle.
