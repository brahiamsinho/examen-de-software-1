# Modelia architecture

Modelia is a multi-tenant UML CASE tool. This document describes the code that
exists in the repository as of the 2026-10-31 audit. Historical implementation
details remain in `CURRENT_STATE.md` and `DECISIONS_LOG.md`.

## System boundaries

| Unit | Responsibility |
| --- | --- |
| `backend/` | Django Ninja/Channels API, domain logic, persistence and generation pipeline. |
| `frontend/` | Next.js workspace, tenant/document UI and Cytoscape UML canvas. |
| `mobile/` | Flutter client: manual OpenAPI connection, screen designer and offline queue. |
| `runner/` | Isolated service that builds and runs generated Spring applications. |
| `openspec/` | Current capability specifications and archived implementation changes. |
| `docs/ai/` | Living engineering context and handoff material. |

Every client reaches the backend over explicit HTTP or WebSocket contracts.
Environment variables configure hosts, ports, credentials and deployment URLs;
those values are not application constants.

## Core model and document flow

`CanonicalUmlModel` is the semantic source of truth. A persisted
`ProjectDocument` stores the UML model separately from `DiagramLayout`, so
canvas positions do not change semantics. Commands mutate a document through
the command bus, validation runs on the canonical model, persistence advances a
revision, and Channels broadcasts accepted changes to collaborators.

```text
Web / mobile / XMI / assistant
        -> validated UML command or import
        -> ProjectDocument + CanonicalUmlModel
        -> persistence, revision and realtime broadcast
        -> canvas, XMI export, relational mapping and generation
```

## Tenant and authorization boundary

Users belong to organizations through memberships. Tenant-bound records inherit
the organization boundary and are obtained through organization-scoped managers;
document/deployment routes resolve membership before accessing tenant data. This
is application-level isolation, not PostgreSQL Row Level Security. New
tenant-bound models must keep this convention and must not use unscoped access
paths.

## Generation and deployment flow

The relational mapper deterministically converts a canonical UML model into
tables, columns, constraints, enums and relationships. The Spring generator
renders a Gradle/Spring Boot project from that relational model. Generation
export produces a deterministic archive; the runner validates it and starts a
restricted deployment behind `/gen/<id>`.

```text
CanonicalUmlModel -> RelationalModel -> Spring generated sources -> ZIP
    -> runner -> isolated generated application -> /gen/<id>/v3/api-docs
```

The generated application's OpenAPI document is also consumed by the Flutter
manual-connection feature.

## Integration paths

- **XMI:** `xmi_interop` imports guarded XMI into the canonical model and
  exports Enterprise Architect-compatible XMI.
- **AI assistance:** voice and image input become validated UML command payloads;
  models do not write directly to the document store.
- **Web canvas:** Cytoscape renders document state, commands and relationship
  hints. Keyboard and assistive-technology behavior still needs a dedicated
  smoke test.
- **Mobile:** Flutter normalizes a generated deployment URL, fetches its
  OpenAPI 3 contract, exposes endpoint discovery and can compose simple local
  screen designs.

## Runtime topology

Development Compose runs the backend, frontend, PostgreSQL, Redis and runner.
Production puts Caddy at the public edge; database, Redis and runner-management
interfaces stay private. Development currently gives the runner a raw Docker
socket, while production uses a restricted socket proxy. Generated deployments
remain a separate runtime boundary and must not receive platform secrets.

## Verification and traceability

OpenSpec capabilities define behavior. Archived changes retain implementation
history; `CURRENT_STATE.md`, `HANDOFF_LATEST.md` and `NEXT_STEPS.md` retain
operational context. On 2026-10-31, frontend Vitest passed with 430 tests and
Flutter analysis/tests passed with 0 issues and 105 tests. Backend pytest still
requires intentionally running the Compose backend and database services.
