# Architecture

This describes the **target** architecture derived from `product-04-next-django.md`
(the frozen spec) at a conceptual level — not a description of code that
exists today. See the "Status today" marker under each section. For the
overall roadmap and cycle order, see `NEXT_STEPS.md` and spec section 37.

## Top-level layout

```
backend/   Django + Django Ninja project (the CASE tool's own backend)
frontend/  Next.js + TypeScript project (the CASE tool's own frontend)
mobile/    Flutter project — real client for the CASE tool (instructor requirement)
docs/ai/   persistent living project memory
openspec/  SDD change/spec store (proposals, specs, tasks, archive)
```

`backend/`, `frontend/`, and `mobile/` remain independently buildable units
communicating only over explicit contracts (HTTP/WebSocket via
environment-configured URLs) — never hardcoded hosts. This has not changed
from the original scaffold; what changes is what each unit is being built
towards.

**Status today**: only this top-level layout and basic infra
(Docker Compose, env-driven config) exist. No domain code below has been
implemented yet.

## Core concept: `CanonicalUmlModel`

The single source of truth for a UML class model. Every input path (manual
edit, image recognition, voice command, XMI import) produces or mutates
this model; every output (canvas rendering, XMI export, relational mapping,
code generation, Domain Manifest) is derived from it. The canvas is a
projection, never authoritative.

**Status today**: implemented as a pure, DB-free dataclass model in
`backend/apps/uml_modeling/domain/` (SDD Cycle 1, change
`canonical-uml-model`): `CanonicalUmlModel`/`UmlModel`, `UmlClass`,
`UmlAttribute`/`UmlOperation`/`UmlParameter`, `Enumeration`/
`EnumerationLiteral`, `Relationship`/`RelationshipEnd`/`Multiplicity`,
and `generation_metadata`. No package/namespace nesting this cycle (flat
model root). No persistence yet.

## `ProjectDocument` / `DiagramLayout` split

Each project is a `ProjectDocument` (UUID, metadata, owner, optimistic
`revision`, timestamps) that holds two children:

- `UmlModel` — the semantic UML content (classes, attributes, relations,
  multiplicities, enums, packages).
- `DiagramLayout` — purely visual data (node positions, etc.), kept
  separate so visual-only changes don't collide with semantic ones and so
  the model can be reused for non-visual purposes (generation, export).

**Status today**: implemented as a pure dataclass envelope
(`backend/apps/uml_modeling/documents.py`, SDD Cycle 1): `ProjectDocument`
(UUID `id`, `ProjectMetadata`, opaque non-empty `owner_id`, `revision`,
timestamps) holding one `CanonicalUmlModel` and one `DiagramLayout`,
with `with_model`/`with_layout` each incrementing `revision` by exactly
one given an explicit `now`. Shape and pure rules only — no ORM,
persistence, or auth yet; no optimistic-concurrency enforcement this
cycle (explicit tech debt).

## Validation engine

One validation engine, reused unmodified across every entry point: manual
save, XMI import, realtime collaboration, the assistant pipeline, and code
generation. Diagnostics carry `severity`, `code`, message, a logical path,
and (when applicable) a reference to the offending model element, so the UI
can jump from a diagnostic straight to the element. Errors block
persistence/generation; warnings do not block by default.

**Status today**: implemented (`backend/apps/uml_modeling/validation/`,
SDD Cycle 1): a single `validate(model) -> ValidationResult` entry
point running the complete, fixed 10-rule Cycle-1 registry
(`EMPTY_ELEMENT_NAME`, `DUPLICATE_CLASS_NAME`, `DUPLICATE_ATTRIBUTE_NAME`,
`DUPLICATE_ENUMERATION_LITERAL`, `UNKNOWN_ATTRIBUTE_TYPE`,
`INVALID_RELATIONSHIP_ENDPOINT`, `INVALID_MULTIPLICITY`,
`GENERALIZATION_CYCLE`, `SELF_ASSOCIATION`, `CLASS_WITHOUT_ATTRIBUTES`),
declared as an explicit static tuple in `engine.py` and never
short-circuiting. Not yet wired to any entry point (HTTP, Channels, XMI,
assistant) — those callers don't exist yet either.

## `UmlCommand` / Command Bus / Undo-Redo pipeline

All local mutation flows through one pipeline:

```
adapter → UmlCommand → UmlCommandBus → UmlCommandExecutor → ProjectDocument
```

Undo/Redo (initial cap: 100 operations) is built on top of this same
pipeline (snapshots or compensating commands), and realtime collaboration
is expected to reuse the same conceptual command contract rather than
inventing a parallel mutation path. This is deliberate: one mutation path
means validation, undo/redo, and collaboration never drift apart.

**Status today**: not implemented — planned after validation (spec order
item 4), with the Cytoscape.js canvas as the primary adapter.

## API layer — Django Ninja

The backend exposes its API via **Django Ninja** (replacing the originally
scaffolded Django REST Framework), which also drives OpenAPI generation for
the CASE tool's own API. Auth uses Django Auth + PyJWT + Argon2 password
hashing.

**Status today**: migration from DRF to Ninja is in progress by a parallel
workstream at the time of writing (not yet confirmed complete — see
`CURRENT_STATE.md`).

### Route protection: server-side + client-side, both layers

Session auth is Django's own `HttpOnly` cookie (`sessionid`), never a
frontend-visible token. Two independent layers enforce protected routes,
neither replacing the other (`ssr-protected-routes`, `frontend-auth-integration`):

- **Server-side** (`frontend/src/lib/server-session.ts`): the `(app)` and
  `(gate)` route-group layouts `await requireUser(nextPath)` before
  rendering anything, validating session *validity* (a real
  `GET /api/auth/me` call), not merely cookie presence, on every
  direct/no-JS request. An anonymous or invalid session never reaches
  protected markup; a backend outage renders normally instead of
  redirecting (an outage must never be misread as a logout).
- **Client-side** (`SessionGuard`): owns the loading skeleton, the
  error/retry UI for a failed session check, and mid-session expiry —
  none of which a navigation-time server check can observe.

**Deployment precondition**: the server-side check works only when the
browser sends the Django `sessionid` cookie to the Next.js origin — true
for `localhost` and same-parent-domain deploys. A split-domain deployment
(e.g. `app.example.com` frontend, `api.example.com` backend) breaks it:
every authenticated user would be redirected to `/login`, since the
cookie set for the API's domain never reaches the frontend's server-side
request. Solving that (a shared parent domain, or a session/token bridge)
is out of scope for the current implementation.

## Realtime layer — Channels/Daphne

Collaboration is realtime, server-authoritative: **Django Channels +
Daphne** (ASGI) on the server, native WebSocket on the client. Each accepted
operation is checked against a `baseRevision`, persisted immediately,
broadcast to other participants, and stale/conflicting operations are
rejected with document recovery on divergence. No full-document echo per
edit; no full CRDT in the MVP. Presence (cursors, selection, connected
sessions) is transmitted separately from `ProjectDocument` and does not
advance its revision.

**Status today**: not implemented as a feature; ASGI/Channels/Daphne
bootstrap is in progress by a parallel workstream (infra only, no
collaboration logic yet).

## `RelationalMapper` — UML → relational

A deterministic transformation from `CanonicalUmlModel` to a
`RelationalModel` (tables, columns, PKs, FKs, unique constraints, indexes),
following documented, fixed rules for associations, aggregation,
composition, generalization, enums, nullability, and constraints. This
mapping is rule-based, not AI-decided at runtime.

**Status today**: not implemented — mid/late-cycle target (spec order item
11), after collaboration and persistence are stable.

## Code generator — Spring Boot backend

Regardless of the CASE tool's own stack, every backend it generates for end
users is **fixed**: Java 21 LTS + Spring Boot 4.x + Gradle + Spring Web MVC
+ Spring Data JPA + Hibernate + Jakarta Validation + Jackson +
springdoc-openapi + PostgreSQL, generated via Jinja2 + LibCST (no manual
string concatenation of source code). This also produces the OpenAPI spec
(via Django Ninja's own OpenAPI on the *tool's* side, springdoc-openapi on
the *generated* side, depending on which artifact is being described) and a
derived Postman collection.

**Status today**: not implemented — a late-cycle target (spec order items
12–16), after the relational mapper.

## `Domain Manifest`

A generated artifact (derived from the model and/or OpenAPI) describing
entities, attributes, types, relations, aliases, searchable/sortable
fields, allowed operations, validations, and CRUD capabilities — the
metadata surface the generated app's assistant is allowed to act on.

**Status today**: not implemented — depends on the generator and OpenAPI
existing first.

## `AssistantCommand` pipeline (text/voice → intent → validated command → executor)

Both in the CASE tool itself (editing assistant) and in generated
applications (end-user assistant), natural language or voice input flows
through: STT (Vosk, Spanish, local) when input is audio → local LLM
inference (Qwen3 via ONNX Runtime + Optimum) → a small closed intermediate
language (`LIST/GET/SEARCH/CREATE/UPDATE/DELETE/COUNT`) → validation against
allow-listed operations/entities/fields → an executor that applies only
validated commands. The AI never emits SQL, executable code, or arbitrary
URLs, and never writes directly to the model or backend without going
through validation.

**Status today**: not implemented — a late-cycle target (spec order items
19–23), after the generator and Domain Manifest exist.

## Image-to-UML and XMI (secondary input paths)

- Image → UML: OpenCV-Python preprocessing → Moondream (ONNX Runtime +
  Optimum) → structured representation → the same validation engine →
  `CanonicalUmlModel`. Never applied without validation.
- XMI 2.1 import/export via `defusedxml` + `lxml`, targeting interoperability
  with Enterprise Architect, as an alternate path into/out of the same
  canonical model.

**Status today**: not implemented — explicitly the last items in the
recommended implementation order (spec section 37, items 25–26), since the
spec states AI/vision/generation must not precede stabilization of the
canonical model, validation, and the single mutation path.

## Mobile architecture (two distinct concerns)

- `mobile/` (Flutter) is a real client of the CASE tool itself — required
  by the instructor, independent of the document's own Android strategy.
  Its scope is not yet defined beyond the bare scaffold.
- The **generated** applications' Android output is produced by wrapping
  the generated Next.js frontend with **Capacitor** (Next.js PWA +
  Capacitor), per spec section 26 — this is a code-generation target, not
  part of `mobile/`.

These are independent requirements from independent sources (instructor vs.
spec document) and both must be satisfied; see `PROJECT_VISION.md` for the
explicit clarification.
