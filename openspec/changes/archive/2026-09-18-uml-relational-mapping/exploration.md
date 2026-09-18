# Exploration: UML → RelationalModel mapping (spec §21) — first step toward the Spring Boot generator (§22)

## Current State

- `product-04-next-django.md` §21 mandates a deterministic
  `CanonicalUmlModel → RelationalMapper → RelationalModel` pipeline
  (tables/columns/PKs/FKs/unique constraints/indexes/relations), with
  explicit documented rules required for: class→table, attribute→column,
  identifier→PK, 1:1/1:N/N:M, composition, herencia (inheritance), enums,
  nullability, constraints. "La IA no decidirá estas reglas en runtime" —
  rules must be fixed at design time.
- §22 mandates the generated backend itself: Java 21 LTS + Spring Boot
  4.x + Gradle + Spring Web MVC + Spring Data JPA + Hibernate + Jakarta
  Validation + Jackson + springdoc-openapi + PostgreSQL, generated via
  Jinja2 + LibCST into a `domain/persistence/application/api/validation/
  errors/config` layout. This is a separate, larger concern from §21.
- §23 requires per-entity CRUD/pagination/sorting/filtering/search/count/
  relation-navigation, derived from structural metadata (not parsed
  operation names).
- §25 requires OpenAPI (native Django Ninja) + Postman Collection,
  downstream of the generated backend.
- §28 Domain Manifest: derived from the model and/or OpenAPI, containing
  entities/attributes/types/relations/aliases/searchable+sortable
  properties/allowed operations/validations/CRUD capabilities/logical
  mapping — consumed later by the assistant executor (§29). It is NOT the
  RelationalModel and not produced by the RelationalMapper; it is
  downstream of the generated backend/OpenAPI.
- §37 (implementation order) and `docs/ai/CURRENT_STATE.md`'s "Pending"
  section agree: 11. UML→RelationalModel, 12. Spring Boot generator, 13.
  generated backend compilable, 14. OpenAPI, 15. Postman, 16. Domain
  Manifest. CURRENT_STATE.md confirms items 11–26 are **all "not started."**
- Codebase check (`backend/`): grepped case-insensitively for
  `relational`, `RelationalModel`, `DomainManifest`, `spring`, `jinja`,
  `libcst`, `generator` across `backend/` — **zero matches**. Genuine
  blank slate; no scaffolding, no partial mapper, no generator toolchain.
- The existing domain layer (`backend/apps/uml_modeling/domain/`, source
  of truth) is small and stable:
  - `CanonicalUmlModel` (`domain/model.py`) — classes, enumerations,
    relationships tuple + lookup helpers.
  - `UmlClass` (`domain/elements.py:65`) — `id`, `name`, `visibility`,
    `attributes`, `operations`. **No PK/identifier flag, no `isAbstract`
    flag.**
  - `UmlAttribute` — `id`, `name`, `type: AttributeType`, `visibility`.
    **No unique/PK metadata.**
  - `AttributeType = PrimitiveType | EnumerationRef` (closed union, 8
    primitives). Class-to-class links can never be an attribute type —
    enforced in `__post_init__` — only ever a `Relationship`.
  - `Relationship` (`domain/elements.py:95`) — `id`,
    `kind: RelationshipKind` (ASSOCIATION/AGGREGATION/COMPOSITION/
    GENERALIZATION), `source`/`target: RelationshipEnd` (`class_id` +
    `Multiplicity(lower, upper)` + optional `role`), optional `name`.
  - `Multiplicity` is deliberately unvalidated at construction (range
    checking lives solely in the `INVALID_MULTIPLICITY` rule);
    `upper=None` means unbounded.
  - `Enumeration`/`EnumerationLiteral` — referenced via
    `EnumerationRef(enumeration_id)`, never by name.
  - **Generalization direction is normative**: `source` = child, `target`
    = parent (confirmed in the dataclass docstring and
    `validation/rules/relationships.py::generalization_cycle`).
  - **Critically: the domain model does NOT restrict a class to a single
    parent.** `generalization_cycle` builds
    `children_of: dict[class_id, list[class_id]]` — one child can have
    multiple `GENERALIZATION` relationships as source, each to a
    different parent. Only *cycles* are rejected (the fixed 11-rule
    registry). Multiple inheritance is therefore currently *modelable*,
    even though standard JPA inheritance strategies (SINGLE_TABLE/
    JOINED/TABLE_PER_CLASS) assume a single-parent tree.
- Project convention (Cycles 1–14): build a pure, DB-free,
  framework-agnostic domain module first (mirroring Cycle 1's
  `CanonicalUmlModel`), unit-tested with `pytest`/`hypothesis`, before
  persistence/generation/UI. One Django app per bounded domain
  (`uml_modeling`, `uml_documents`, `uml_commands`, `users`,
  `organizations`) — no app mixes concerns.
- The Django app itself already establishes a UUID-primary-key convention
  across every model (`users`, `organizations`, `uml_documents`) —
  relevant context for the PK-source open question below.

## Affected/New Areas

- New Django app, e.g. `backend/apps/relational_mapping/` (per the
  app-per-domain convention, not inside `uml_modeling/`) — a
  `RelationalModel` domain module (tables/columns/PKs/FKs/uniques/indexes
  as frozen dataclasses, mirroring `uml_modeling/domain/`'s style) plus a
  pure `RelationalMapper` consuming `CanonicalUmlModel`.
- `backend/apps/uml_modeling/domain/elements.py` / `types.py` — touched
  only if new metadata is added (e.g. a PK/identifier marker on
  `UmlAttribute`, an `isAbstract` marker on `UmlClass`) — itself a design
  fork, not to be assumed.
- `backend/apps/uml_modeling/validation/` — a new rule may be needed if a
  design decision requires rejecting unmappable models (e.g. multi-parent
  generalization) rather than the mapper silently choosing something.
- Untouched: `uml_documents/`, `uml_commands/` (mapper only reads
  `CanonicalUmlModel`), and everything under §22-28 (Java/Gradle,
  Jinja2/LibCST, OpenAPI, Postman, Domain Manifest) — explicitly later in
  the ordering.

## Approaches

1. **RelationalModel domain model + deterministic mapper only, no
   persistence/generation** — pure Python module (mirroring Cycle 1's
   style): `RelationalModel`/`Table`/`Column`/`PrimaryKey`/`ForeignKey`/
   `UniqueConstraint`/`Index` as frozen dataclasses, plus
   `map_to_relational(model) -> RelationalModel`, fully unit-tested, zero
   Django models/migrations, zero Java/Jinja2/LibCST.
   - Pros: smallest true forward-progress increment; matches the
     established "pure domain first" convention; isolates and forces
     resolution of the real design forks in one reviewable, testable
     artifact; low blast radius; comfortably fits the review budget.
   - Cons: no runnable/visible artifact yet (no SQL, no compiled backend)
     — purely structural.
   - Effort: Low–Medium.

2. **Mapping + a minimal one-entity Spring Boot skeleton** (introduce
   Jinja2/LibCST + Java/Gradle now too).
   - Pros: proves the toolchain end-to-end sooner.
   - Cons: bundles a genuine unresolved domain-design decision with a
     brand-new polyglot toolchain in one change; very likely exceeds the
     review-budget guard; contradicts §37's explicit separation of item
     11 from item 12; would be built on assumptions the open questions
     below haven't resolved yet.
   - Effort: High.

3. **Full generator end-to-end (mapping + templates + compilation +
   generator tests, §34) in one change.**
   - Pros: none beyond fewer PRs.
   - Cons: massively oversized for one SDD cycle; contradicts this
     project's demonstrated cycle-by-cycle discipline; mixes unrelated
     risk profiles (pure logic vs. codegen vs. compilation) in one
     review.
   - Effort: Very High.

## Recommendation

Approach 1 — a standalone `RelationalModel` + `RelationalMapper`
pure-domain module, no persistence, no generation. Matches how Cycle 1
(`CanonicalUmlModel`) was built and how every subsequent cycle has stayed
single-concern. It's also the only approach that forces the real design
decisions below to be resolved explicitly and reviewably, rather than
baking untested assumptions into a generator or Java skeleton that would
be expensive to unwind later.

## Risks

- The domain model currently permits multiple `GENERALIZATION` parents
  per class (no single-inheritance constraint) — any mapping-strategy
  decision must either handle this or a new validation rule must reject
  it first; picking a JPA-style single-inheritance strategy without
  addressing this will produce an incomplete/silently-lossy mapper.
- `UmlAttribute` has no PK/identifier/uniqueness metadata today —
  "identificador → PK" (§21) needs a source of truth: implicit synthetic
  PK for every class, or new domain metadata (a design fork, see Open
  Questions).
- `Multiplicity.upper == None` and unvalidated ranges (e.g. `0..0`) mean
  the mapper must decide its own behavior for edge cases the domain layer
  intentionally does not reject at construction time.
- §22 explicitly requires the generated-backend stack (Java/Spring Boot)
  stay fully independent of the main tool's own stack — a future
  generator implementer must not reuse Django/Python patterns for the
  generated output.

## Open Questions (for the user, before proposal)

1. **Inheritance/generalization mapping strategy**: single-table
   (discriminator column), joined (table-per-subclass with shared-PK FK
   chain), or table-per-concrete-class? Most consequential fork — affects
   PK/FK design and how the current *multi-parent-permitting* domain
   model must be constrained (a single-inheritance JPA strategy can't
   represent a class with two independent generalization parents without
   extra design work).
2. **Enumeration mapping**: native PostgreSQL `ENUM` type, a lookup table
   (FK from referencing columns), or `VARCHAR` + `CHECK` constraint?
3. **Primary key source**: synthetic generated PK (UUID) for every table
   unconditionally (matches this app's own existing UUID-PK convention),
   or extend `UmlAttribute` with an explicit "is identifier" marker
   (currently absent) that the mapper honors when present, falling back
   to synthetic otherwise?
4. **Relationship → FK/join-table rules**: do association/aggregation/
   composition differ *structurally* in the relational output (e.g.
   composition's FK gets `NOT NULL` + `ON DELETE CASCADE` reflecting
   whole/part lifecycle ownership, while association/aggregation stay
   plain nullable FKs), or do all three collapse to the same generic
   "FK on the many side, join table when both ends are many" rule with no
   cascade differentiation?
5. **Nullability derivation** (lower priority, can default to a sensible
   rule at design time): does `Multiplicity.lower == 0` on a relationship
   endpoint mechanically drive a nullable FK column?
6. **Self-referencing relationships** (lower priority, already
   warned-on for ASSOCIATION via `SELF_ASSOCIATION`): any special-case
   handling beyond the generic rule, e.g. a self-referencing composition
   (tree structure)?

## Ready for Proposal

Pending resolution of at minimum Open Questions 1-4 (5-6 can default to a
reasonable rule at design time if not raised explicitly).
