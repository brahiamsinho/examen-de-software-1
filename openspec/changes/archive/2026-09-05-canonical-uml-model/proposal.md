# Proposal: Cycle 1 — Canonical UML Model, Project Document, Validation Engine

## Intent

The repository is a correctly-aligned infra skeleton with zero domain logic. Every
later feature in `product-04-next-django.md` (canvas, command bus, persistence,
realtime, relational mapping, generation, assistant, XMI, vision) reads or writes
one structure — the canonical UML model — and section 37 explicitly forbids AI,
vision, and generation from preceding its stabilization. Cycle 1 therefore
establishes that convergence point plus its document envelope and its single
validation engine, so all later cycles build on a frozen, tested contract instead
of negotiating shapes ad hoc.

## Scope

### In Scope (section 38 cycle shape)

**Objective**: a DB-free, framework-agnostic canonical UML domain with a reusable
validation engine.

Use cases (project-local identifiers, not copied from any other project):

- `UML-C1-1` — Represent a UML class diagram as a `CanonicalUmlModel` (classes,
  attributes, operations, visibility, primitive types, enumerations,
  association/aggregation/composition/generalization, multiplicity).
- `UML-C1-2` — Represent a project as a `ProjectDocument` splitting semantic
  `UmlModel` from visual `DiagramLayout`, with UUID, metadata, owner, revision,
  timestamps.
- `UML-C1-3` — Validate any canonical model through one engine and obtain
  navigable diagnostics (severity, code, message, logical path, element ref).

### Out of Scope

- Canvas/Cytoscape.js, `UmlCommand`/Command Bus, Undo/Redo (items 4, 5, 7).
- Django ORM models, migrations, Postgres, optimistic-revision *enforcement*
  (item 6). Cycle 1 defines the `revision` field and its pure increment rule only.
- Auth, ownership authorization, memberships (item 8).
- Channels/realtime, presence, offline/LAN (items 9, 10).
- Relational mapping, generators, OpenAPI, manifest, assistant, STT, XMI, vision
  (items 11-26).
- HTTP/WS endpoints and Ninja/Pydantic schemas. `schemas.py` is deferred to the
  first cycle that exposes this model.
- `Package` (see D3). Frontend and mobile: untouched.

## Capabilities

`openspec/specs/` is currently empty; all capabilities are new.

### New Capabilities

- `uml-domain-model`: the `CanonicalUmlModel` structures and their invariants —
  the single convergence point every input channel normalizes to.
- `project-document`: `ProjectDocument` / `UmlModel` / `DiagramLayout` split,
  owner identity, metadata, revision, timestamps.
- `uml-validation`: the single validation engine, diagnostic contract, and the
  Cycle-1 rule set with per-rule blocking policy.

### Modified Capabilities

None.

## Resolved Decisions

The spec leaves the following underspecified. Each is resolved here so downstream
cycles inherit a stable contract instead of a breaking change.

**D0 — `CanonicalUmlModel` vs `UmlModel`.** Section 6 names the semantic content
`UmlModel`; sections 10/21 and section 37 item 1 call it `CanonicalUmlModel`. These
are one structure, not two. We define a single dataclass `CanonicalUmlModel` and
export `UmlModel` as an alias so both spec vocabularies resolve to the same type.
Two distinct types would immediately create a mapping layer with no semantic
purpose and would weaken the "single convergence point" rule.

**D1 — Multiplicity format.** Structured and authoritative:
`Multiplicity(lower: int, upper: int | None)` where `upper=None` means unbounded,
plus pure `parse`/`format` helpers for the UML string syntax (`"1"`, `"0..1"`,
`"0..*"`, `"1..*"`). Rationale: three later consumers need different projections of
the same fact — the canvas needs a display label (section 8), XMI 2.1 needs integer
`lowerValue`/`upperValue` (item 25), and the relational mapper must branch
numerically on 1:1 / 1:N / N:M (section 21). A string-only representation would
force each of them to re-parse; the structured pair is canonical and the string is a
derived projection.

**D2 — Enumeration shape.** `Enumeration` is a top-level model element, a sibling of
`Class`, held in `CanonicalUmlModel.enumerations`, with `id`, `name`, and an
**ordered** `literals: list[EnumerationLiteral]` where each literal has `id`, `name`,
and optional `value: str | None`. Attributes reference an enumeration **by id**, never
by name. Rationale: section 21 requires a deterministic enum→relational rule and
section 27 maps `Enum → select`; both need an identity that survives a rename, which
name-based references do not provide. Literal order is preserved because generated
select options and DB enum ordering must be deterministic across regenerations.
Consequently `AttributeType` is a closed tagged union of `PrimitiveType` or
`EnumerationRef(enumeration_id)`; class-typed attributes are rejected, because
class-to-class links are expressed as `Relationship` and allowing two representations
of an association would make the relational mapper non-deterministic.

**D3 — `Package`: deferred.** Section 7 qualifies it as "cuando sea necesario", the
MVP (section 36) and demo flow (section 35) do not require it, and section 8's canvas
capability list contains no package construct. Cycle 1 therefore uses one flat model
namespace. Rationale: packages introduce nesting, qualified naming, and name
*scoping*, and scoping changes the meaning of the duplicate-name rules in D5 —
adopting packages later is additive, but adopting them now would cost real work with
no consumer. Forward compatibility is preserved by phrasing uniqueness rules over a
"namespace" that today always resolves to the model root, so a later package cycle
replaces a resolver rather than rewriting rules. Logged as explicit tech debt.

**D4 — Attribute data types.** A closed enum of eight primitives: `String`, `Text`,
`Integer`, `Long`, `Decimal`, `Boolean`, `Date`, `DateTime`. Rationale: this is
exactly the primitive set the project has already committed to in section 27's
UI-inference table (excluding its `Enum` row, handled by D2, and its `N:1`/`1:N` rows,
which are relationships not attribute types). Adopting the same set now guarantees the
Cycle-1 domain and the later generation cycle cannot drift. It is a closed enum rather
than a free-form string so validation can reject unknown types deterministically and
the relational mapper needs no fallback branch; adding `UUID` or `Float` later is a
purely additive change.

**D5 — Diagnostic path, element reference, and blocking policy.** Section 10 requires
both a "path lógico" and a "referencia al elemento cuando corresponda", so these are
two separate fields, not one. `path` is a slash-rooted, **id-based** locator:
`/`, `/classes/{classId}`, `/classes/{classId}/attributes/{attributeId}`,
`/enumerations/{enumId}/literals/{literalId}`, `/relationships/{relationshipId}`.
`element_ref` is a structured `ElementRef(kind, id) | None` — the machine handle the UI
uses to select the node on the canvas. Ids rather than names, because names are mutable
and non-unique precisely when a duplicate-name diagnostic is being displayed. A
`Diagnostic` is `(severity, code, message, path, element_ref)` with `code` a stable
SCREAMING_SNAKE identifier, and `severity` restricted to `ERROR` or `WARNING`.

Blocking policy: `ERROR` blocks persistence and generation; `WARNING` never blocks.
Cycle-1 rules:

| Code | Severity | Why |
|---|---|---|
| `EMPTY_ELEMENT_NAME` | ERROR | Unnameable element cannot map to a table/column |
| `DUPLICATE_CLASS_NAME` | ERROR | class→table collision (section 21) |
| `DUPLICATE_ATTRIBUTE_NAME` | ERROR | attribute→column collision within a class |
| `DUPLICATE_ENUMERATION_LITERAL` | ERROR | Non-deterministic enum mapping |
| `UNKNOWN_ATTRIBUTE_TYPE` | ERROR | Unresolvable/ dangling enumeration reference |
| `INVALID_RELATIONSHIP_ENDPOINT` | ERROR | Endpoint id absent from the model |
| `INVALID_MULTIPLICITY` | ERROR | `lower < 0`, or bounded `upper < lower` |
| `GENERALIZATION_CYCLE` | ERROR | Inheritance mapping would not terminate |
| `SELF_ASSOCIATION` | WARNING | Legal UML, frequently unintended |
| `CLASS_WITHOUT_ATTRIBUTES` | WARNING | Legal, but generates an empty table |

The engine MUST collect all diagnostics rather than short-circuit on the first error,
because section 10 requires the UI to navigate a diagnostic list.

**D6 — `ProjectDocument.owner`.** `owner_id: str` — an opaque, non-empty identifier
the domain never interprets, resolves, or authorizes against. Rationale: section 6
requires `propietario` now while Auth is item 8. Django's default user PK is an
integer but the project may later use a UUID; an opaque string is the superset that
maps cleanly onto either via `str(user.pk)`, so the ownership cycle adds a resolver
and authorization filter without changing the domain field's type. The domain package
must not import `django.contrib.auth`, which would drag a DB dependency into a
deliberately DB-free layer. Validating only non-emptiness keeps the placeholder from
encoding a format the real auth backend may not honor.

**D7 — Cross-import rule interpretation.** `openspec/config.yaml`'s "no cross-imports
except through the HTTP/WS API contract" governs the **deployment-unit** boundary
(backend ↔ frontend ↔ mobile), not module boundaries inside `backend/`. Rationale: the
rule sits beside "Follow existing modular-by-default layout: `backend/apps/<feature>/`,
`frontend/src/app/`", and the units it enumerates are separate runtimes. Reading it as
governing Django-app-to-Django-app imports would require an in-process HTTP hop to call
a pure validation function, and would directly contradict section 10's requirement that
one engine be reused by saving, import, collaboration, the assistant, and generation —
all of which live inside `backend/`. Operative rule for this cycle: intra-backend
imports are permitted but MUST be acyclic and one-directional, with the UML domain as a
leaf that imports from no other app. Cycle 1 therefore ships one app; a later
project/ownership app may import the domain, never the reverse. **Flagged for user
override** — if the intended reading is the stricter one, that must be settled before
any second backend app is created.

**D8 — Generator metadata separation.** Section 7 requires "metadatos de generación"
while demanding pure UML elements be clearly distinguished from them. Cycle 1 provides
the structural separation only: a `generation_metadata` container held on
`CanonicalUmlModel` and keyed by element id, never interleaved into the UML element
dataclasses. Its keys are not validated this cycle; section 33's profile (`entity`,
`auditable`, `readOnly`, ...) is defined in the generation cycles. Rationale: reserving
the extension point now costs one field and prevents a breaking shape change later,
while validating an unused profile now would be speculative work.

## Approach

Confirms exploration Approach A. Build the domain as frozen Python dataclasses and the
validation engine as pure functions, fully DB-free, in one new Django app
`backend/apps/uml_modeling/`, registered in `INSTALLED_APPS` with no `models.py`, no
migrations, and no urlconf wiring. Ninja/Pydantic `Schema` adapters are deferred to the
first cycle that exposes an endpoint, keeping the engine callable from every future
entry point (HTTP, Channels, XMI, assistant) as section 10 requires.

```
backend/apps/uml_modeling/
├── apps.py
├── domain/
│   ├── ids.py           # element id type + factory
│   ├── types.py         # PrimitiveType, AttributeType, EnumerationRef, Multiplicity
│   ├── elements.py      # UmlClass, UmlAttribute, UmlOperation, Visibility,
│   │                    # Enumeration, EnumerationLiteral, Relationship, RelationshipKind
│   └── model.py         # CanonicalUmlModel (+ UmlModel alias), lookup helpers
├── documents.py         # ProjectDocument, ProjectMetadata, DiagramLayout
├── validation/
│   ├── diagnostics.py   # Severity, Diagnostic, ElementRef, ValidationResult
│   ├── engine.py        # validate(model) -> ValidationResult; rule registry
│   └── rules/           # naming.py, relationships.py, types.py, multiplicity.py
└── tests/
```

Engine contract: `validate(model: CanonicalUmlModel) -> ValidationResult`, where each
rule is an independently testable `(CanonicalUmlModel) -> Iterable[Diagnostic]`
registered in `engine.py`. `ValidationResult` exposes `diagnostics`, `errors`, and
`is_blocking`.

Strict TDD (RED-GREEN-REFACTOR) per `config.yaml`, one use case at a time. Tests are
plain `pytest` with `hypothesis` property tests for multiplicity parse/format
round-tripping and rule invariants; no `pytest-django` DB fixtures are required.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `backend/apps/uml_modeling/` | New | Entire cycle deliverable |
| `backend/config/settings.py` | Modified | One `INSTALLED_APPS` entry |
| `backend/config/urls.py`, `api.py` | Untouched | No endpoint this cycle |
| `backend/requirements/*` | Untouched | Stdlib only; no new dependency |
| `openspec/specs/` | New | First three capability specs |
| `docs/ai/CURRENT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS_LOG.md`, `NEXT_STEPS.md` | Modified | Dual-documentation convention; D0-D8 go to `DECISIONS_LOG.md` |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| A resolved decision (D1-D4) proves wrong once the relational mapper or XMI import lands | Medium | All are additive-friendly: structured multiplicity, id-based enum refs, and a closed primitive enum extend without breaking readers; changes recorded in `DECISIONS_LOG.md` |
| D7's interpretation contradicts the user's intent for `config.yaml` | Low | Cycle 1 ships a single app, so nothing depends on the permissive reading yet; flagged for explicit confirmation before a second app |
| Deferring `Package` (D3) forces rework if XMI import requires packages | Medium | Uniqueness rules are phrased over a namespace that currently resolves to the model root; adding packages replaces a resolver |
| Deferring persistence leaves `revision` semantics untested end-to-end | Low | Cycle 1 tests only the pure increment rule; conflict detection is explicitly item 9's scope |
| Scope creep into canvas or command-bus concerns | Medium | Out-of-scope list above is explicit; no frontend files in the change |

## Rollback Plan

The cycle adds one self-contained app plus a single `INSTALLED_APPS` line. There are
no models, migrations, routes, dependencies, persisted data, or API consumers, so
rollback is `git revert` of the cycle commits — or deleting `backend/apps/uml_modeling/`
and that one settings line. Nothing outside the app imports it, and no other runtime
(frontend, mobile) is affected.

## Dependencies

- None new. Uses stdlib `dataclasses`, `enum`, `uuid`, `datetime`; `pytest` and
  `hypothesis` are already installed in `backend/requirements/test.txt`.
- `openspec/specs/` is empty and will be bootstrapped by `sdd-spec`.

## Explicit Tech Debt (section 38)

1. `Package` and qualified naming deferred (D3).
2. `owner_id` is an opaque placeholder with no auth resolution (D6).
3. `revision` exists but optimistic-concurrency enforcement is absent (item 6/9).
4. Section 33's generator metadata profile keys are unvalidated (D8).
5. No Ninja/Pydantic serialization boundary; the model is not yet reachable over
   HTTP or WS.
6. `Operation` is modeled structurally but no operation-level validation rules exist.

## Success Criteria

- [ ] `CanonicalUmlModel` represents every section 7 element required by D1-D4,
      with generator metadata structurally separated (D8).
- [ ] `ProjectDocument` carries UUID, metadata, `owner_id`, `revision`, timestamps,
      and cleanly separates `UmlModel` from `DiagramLayout`.
- [ ] One `validate()` entry point produces all ten Cycle-1 diagnostics with correct
      severity, code, path, and element reference.
- [ ] Every diagnostic's `path` and `element_ref` resolve to an element present in
      the validated model.
- [ ] `cd backend && pytest` is green, requiring no database.
- [ ] The domain package imports nothing from Django, Ninja, or Pydantic.
- [ ] `docs/ai/CURRENT_STATE.md` and `DECISIONS_LOG.md` reflect the real post-cycle
      state and decisions D0-D8.
