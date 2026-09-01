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

**Status today**: not implemented. This is the first thing SDD Cycle 1
targets (see `NEXT_STEPS.md`).

## `ProjectDocument` / `DiagramLayout` split

Each project is a `ProjectDocument` (UUID, metadata, owner, optimistic
`revision`, timestamps) that holds two children:

- `UmlModel` — the semantic UML content (classes, attributes, relations,
  multiplicities, enums, packages).
- `DiagramLayout` — purely visual data (node positions, etc.), kept
  separate so visual-only changes don't collide with semantic ones and so
  the model can be reused for non-visual purposes (generation, export).

**Status today**: not implemented — planned for early SDD Cycle 1
(spec order items 1–2).

## Validation engine

One validation engine, reused unmodified across every entry point: manual
save, XMI import, realtime collaboration, the assistant pipeline, and code
generation. Diagnostics carry `severity`, `code`, message, a logical path,
and (when applicable) a reference to the offending model element, so the UI
can jump from a diagnostic straight to the element. Errors block
persistence/generation; warnings do not block by default.

**Status today**: not implemented — planned right after the canonical model
(spec order item 3).

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
