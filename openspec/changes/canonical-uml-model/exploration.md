# Exploration: CanonicalUmlModel, ProjectDocument/DiagramLayout, Validation Engine

Scope: spec `product-04-next-django.md` section 37, implementation-order items 1-3
only. No canvas, persistence, auth, or realtime in this cycle.

## Current State

Zero domain logic exists. Backend is a bare Django 5.0 + Django Ninja 1.x +
Channels/Daphne skeleton, no feature apps yet (`backend/apps/` empty except
`__init__.py`/README instructing `startapp` + `INSTALLED_APPS` + urlconf wiring).
Only endpoint is `GET /api/health`, tested DB-free via `SimpleTestCase`.
`backend/requirements/base.txt` pins `django-ninja>=1.1,<2.0` (vendors Pydantic 2
transitively; no direct `pydantic` pin yet). `test.txt` has pytest/pytest-django/
hypothesis. No Django models exist anywhere.

## Affected Areas

- `backend/apps/` - new feature app(s) per project README convention
- `backend/config/settings.py` - `INSTALLED_APPS` addition
- `backend/config/urls.py` / `api.py` - untouched unless this cycle exposes an
  endpoint (it likely shouldn't yet)
- `backend/requirements/base.txt` - may need explicit `pydantic` pin if imported
  directly
- `docs/ai/CURRENT_STATE.md`, `ARCHITECTURE.md`, `NEXT_STEPS.md`,
  `DECISIONS_LOG.md` - dual-documentation convention requires updates during
  `sdd-apply`

## Approaches (data structure choice)

1. **Dataclasses domain + validation as pure functions; Pydantic/Ninja `Schema`
   only at a future API boundary.** Pros: framework-agnostic, reusable by every
   entry point (HTTP, Channels, XMI, assistant) per spec section 10's single-engine
   requirement; trivial hypothesis testing; no DB coupling. Cons: needs a mapping
   layer later when wiring Ninja/ORM. Effort: Low-Medium. **Recommended.**
2. **Pydantic `BaseModel`/Ninja `Schema` as the domain model directly.** Pros:
   reuses Pydantic 2 already in the stack, zero future mapping. Cons: blurs
   domain/API boundary prematurely, risks splitting business-rule validation
   between Pydantic validators and the spec's mandated single engine, awkward for
   non-HTTP entry points. Effort: Low.
3. **Django ORM models from day one.** Pros: no future mapping. Cons: directly
   contradicts spec section 37 ordering (persistence is item 6, explicitly after
   validation, item 3); forces a DB before the spec intends one; the project's own
   test convention prefers DB-free `SimpleTestCase`. Effort: Medium, misaligned
   with spec intent.

## Recommendation

Build `CanonicalUmlModel`, `UmlModel`, `ProjectDocument`, `DiagramLayout`, and the
validation engine as plain dataclasses + pure functions in one new app,
tentatively `backend/apps/uml_modeling/`, fully DB-free (pytest + hypothesis only,
no pytest-django DB fixtures needed). Defer Django ORM models/migrations to spec
item 6. Structure: `domain/elements.py`, `domain/model.py`, `documents.py`,
`validation/{diagnostics,engine,rules/}`, `schemas.py` (deferred), `tests/`.

## Open Questions / Risks (quoted from spec)

- Section 7: "Operation cuando corresponda" / "Package cuando sea necesario" -
  conditionally required, ambiguous scope for Cycle 1.
- Section 7: data type list ("tipos de datos") never enumerated; section 27's
  UI-inference table is a generation-cycle artifact, not a confirmed Cycle-1 type
  list.
- Multiplicity format undefined anywhere in the spec.
- Enumeration shape (top-level element? reference-by-id vs name? literal values?)
  undefined.
- Package nesting depth/qualified-naming rules undefined.
- Section 7: "Se distinguiran claramente los elementos UML puros de los metadatos
  propios del generador" vs section 33's generator metadata profile - unclear if
  Cycle 1 needs an extension point now.
- Section 10 diagnostic `path`/element-reference format unspecified; section 10
  "cuando corresponda" leaves per-rule blocking policy underspecified.
- Section 6 requires `ProjectDocument.owner` now, but Auth+ownership is item 8
  (much later) - genuine ordering tension; a placeholder identifier type is
  needed.
- `openspec/config.yaml`'s "no cross-imports except through the HTTP/WS API
  contract" rule is ambiguous as to whether it governs intra-backend Django-app
  imports, affecting whether a future 2-app split (domain vs. project/ownership)
  is permitted.

## Prior Art

- EMF/GMF-style tools separate abstract-syntax (semantic) model from notation
  (diagram) model - matches the `UmlModel`/`DiagramLayout` split and spec section
  8's "canvas never authoritative."
- Idiomatic Django Ninja + Pydantic pattern: ORM for persistence, Pydantic
  `Schema` only at the API boundary, business validation kept independent of
  both - supports the dataclass-domain recommendation.
- The spec's own upcoming `UmlCommand`/CommandBus (item 4) argues against an ORM
  active-record model now, since command-mediated mutation (not direct model
  writes) is meant to be the single mutation path.

## Ready for Proposal

Yes - scope is clear (spec section 37 items 1-3 only); the open questions above
are the concrete decision list for `sdd-propose`.
