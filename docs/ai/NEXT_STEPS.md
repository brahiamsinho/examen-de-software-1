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

## Immediate next step: SDD Cycle 1

Per the spec's own recommended implementation order
(`product-04-next-django.md`, section 37, items 1–3), the next actual
feature work is:

1. Run **`sdd-explore`** to investigate and derive concrete use cases for:
   - `CanonicalUmlModel` — the core UML domain model (classes, attributes,
     operations, visibility, associations/aggregation/composition/
     generalization, multiplicity, enumerations, packages);
   - `ProjectDocument` / `DiagramLayout` — the persistence envelope
     (UUID, owner, optimistic revision, timestamps) split from purely
     visual layout data;
   - the validation engine (single engine, structured diagnostics with
     severity/code/message/path/element reference) that will later be
     reused by save, import, collaboration, the assistant, and generation.
2. Run **`sdd-propose`** once exploration produces clear use cases and
   acceptance criteria, keeping this first cycle scoped to just those
   three pieces — do not pull in canvas, persistence wiring, Undo/Redo,
   auth, or realtime yet; those are separate later cycles per section 37.
3. Continue through `sdd-spec` → `sdd-design` → `sdd-tasks` → `sdd-apply`
   → `sdd-verify` → `sdd-archive` for this first cycle, updating
   `CURRENT_STATE.md` and this file as it progresses.

## After Cycle 1

Following spec section 37's order: canvas (Cytoscape.js) → persistence
(Django ORM) → Undo/Redo → auth/ownership → realtime (Channels/Daphne) →
presence → UML→relational mapping → Spring Boot generator → OpenAPI/Postman
→ Domain Manifest → frontend generator → generic CRUD → assistant pipeline
→ voice/STT → Android (Capacitor) → XMI → image-to-UML. Do not front-load
AI/vision/generation work ahead of a stable canonical model, validation,
and single mutation path — the spec is explicit about this ordering
constraint.

## Also outstanding (from the original scaffold, still valid)

- Design and build real Flutter screens under `mobile/lib/` for the CASE
  tool client (instructor requirement) once there is a domain model to
  build a UI against — this should follow, not precede, the backend
  domain work above.
- Once auth exists (SDD Cycle covering item 8, Auth + ownership), thread
  it through the Next.js frontend, the Flutter client, and any generated
  clients.
