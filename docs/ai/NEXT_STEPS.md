# Next Steps

## Stack correction / bootstrap work (in progress)

The stack-correction work described in `DECISIONS_LOG.md` and
`TECH_STACK.md` — Django Ninja + Channels/Daphne + Argon2/PyJWT +
pytest bootstrap on the backend, and Tailwind/shadcn/Cytoscape/Jotai +
Vitest bootstrap on the frontend — is being carried out by parallel
workstreams. Verify its actual completion (health-check endpoint + smoke
tests on backend, smoke test on frontend) before treating it as done in
`CURRENT_STATE.md`. Cypress (E2E) bootstrap has not been started and
should follow once the frontend stack settles.

## SDD Cycle 1 — status: implemented, pending verify/archive

Per the spec's own recommended implementation order
(`product-04-next-django.md`, section 37, items 1–3), Cycle 1
(`canonical-uml-model`) covers `CanonicalUmlModel`, `ProjectDocument`/
`DiagramLayout`, and the validation engine.

- explore → propose → spec → design → tasks → **apply**: done.
  `backend/apps/uml_modeling/` implements the full domain layer, the
  `ProjectDocument` envelope, and the 10-rule validation engine, with 80
  passing backend tests (strict TDD) and zero regression to the
  pre-existing health-check smoke test.
- Remaining for this cycle: **`sdd-verify`** (confirm the implementation
  against `openspec/changes/canonical-uml-model/specs/**` and
  `design.md`), then **`sdd-archive`**.
- Deliberately out of scope this cycle (do not pull in yet): canvas,
  persistence wiring (Django ORM/migrations), Undo/Redo, auth/ownership
  resolution, or realtime — those are separate later cycles per section 37.

## After Cycle 1

Following spec section 37's order: `UmlCommand` + Command Bus → canvas
(Cytoscape.js) → persistence (Django ORM) → Undo/Redo →
auth/ownership → realtime (Channels/Daphne) →
presence → UML→relational mapping → Spring Boot generator → OpenAPI/Postman
→ Domain Manifest → frontend generator → generic CRUD → assistant pipeline
→ voice/STT → Android (Capacitor) → XMI → image-to-UML. Do not front-load
AI/vision/generation work ahead of a stable canonical model, validation,
and single mutation path — the spec is explicit about this ordering
constraint.

## Spring Boot generator — relationships (FK) + enum types — status: implemented, pending verify/archive

`2026-09-18-spring-boot-generator-relationships-enums` (extends
`2026-09-18-spring-boot-generator-core`) lifts the FK and enum-column
rejections `generate_table_sources` had before: FK columns now render as
`@ManyToOne`/`@OneToOne` + `@JoinColumn` relationship fields (including the
self-referencing case), enum-typed columns render as
`@Enumerated(EnumType.STRING)` fields, and a new `generate_enum_source`
turns an `EnumType` into a standalone Java enum.

- explore → propose → spec → design → tasks → **apply**: done. 40 new
  backend tests, 576/576 backend tests pass, single PR
  (`size:exception`, confirmed by the user).
- Remaining for this cycle: **`sdd-verify`** (confirm the implementation
  against `openspec/changes/2026-09-18-spring-boot-generator-relationships-enums/specs/**`
  and `design.md`), then **`sdd-archive`**.
- Explicit follow-ups, deliberately out of scope this cycle (proposal Out
  of Scope): **Single Table inheritance generation** (structurally blocked
  — `Column` has no owning-UML-class attribution), bidirectional
  `@OneToMany` inverse collections, `@ManyToMany`/`@JoinTable` join-table
  detection or suppression, cross-artifact Java class-name collision
  detection (e.g. a table `order` vs an enum `order`), and any
  orchestrating caller that walks a whole `RelationalModel` and combines
  per-table/per-enum output.

## Also outstanding (from the original scaffold, still valid)

- Design and build real Flutter screens under `mobile/lib/` for the CASE
  tool client (instructor requirement) once there is a domain model to
  build a UI against — this should follow, not precede, the backend
  domain work above.
- Once auth exists (SDD Cycle covering item 8, Auth + ownership), thread
  it through the Next.js frontend, the Flutter client, and any generated
  clients.
