# Proposal: UML → RelationalModel deterministic mapping (spec §21)

## Intent

`product-04-next-django.md` §21 requires a deterministic `CanonicalUmlModel → RelationalMapper → RelationalModel` pipeline with rules fixed at design time ("La IA no decidirá estas reglas en runtime"). Nothing exists today (§37 item 11, all of 11–26 "not started"). Every downstream deliverable — Spring Boot generator (§22), CRUD API (§23), OpenAPI/Postman (§25), Domain Manifest (§28) — depends on this relational shape. Building it as a pure, unit-tested domain module first (as Cycle 1 did for `CanonicalUmlModel`) resolves the mapping forks explicitly and reviewably instead of burying them in a code generator.

## Scope

### In Scope
- New Django app `backend/apps/relational_mapping/` with a pure `domain/` module: `RelationalModel`, `Table`, `Column`, `PrimaryKey`, `ForeignKey`, `UniqueConstraint`, `Index`, `EnumType` as frozen dataclasses.
- Pure `map_to_relational(CanonicalUmlModel) -> RelationalModel`, deterministic, DB-free, framework-agnostic.
- Documented mapping rules for: class→table, attribute→column, PK, 1:1 / 1:N / N:M, composition, generalization, enums, nullability, constraints.
- New validation rule rejecting multi-parent generalization (Single Table requires a single-parent tree).
- Full `pytest` / `hypothesis` unit coverage (strict TDD).

### Out of Scope
- §22 Spring Boot / Java 21 / Gradle generator, Jinja2 + LibCST toolchain.
- §23 generated CRUD/pagination/filter endpoints.
- §25 OpenAPI + Postman Collection. §28 Domain Manifest.
- DDL/SQL emission, Django models, migrations, persistence, HTTP/WS surface, UI.

## Capabilities

### New Capabilities
- `relational-mapping`: RelationalModel structure and the deterministic UML→relational mapping rules.

### Modified Capabilities
- `uml-validation`: add an ERROR rule rejecting a class with more than one `GENERALIZATION` parent.

## Approach

Exploration Approach 1. Settled design constraints (user-confirmed):

| Fork | Decision |
|---|---|
| Inheritance | Single Table + discriminator column; single-parent only |
| Enumerations | Native PostgreSQL `ENUM` type |
| Primary key | Synthetic UUID PK on every table, unconditional; no new UML metadata |
| Composition | FK `NOT NULL` + `ON DELETE CASCADE` |
| Association / aggregation | Plain nullable FK; join table when both ends are many |

Nullability from `Multiplicity.lower` and self-referencing relationships default to a rule chosen in `sdd-design`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/apps/relational_mapping/` | New | Domain dataclasses + mapper + tests |
| `backend/apps/uml_modeling/validation/rules/relationships.py` | Modified | Multi-parent generalization rule |
| `backend/config/settings/` | Modified | Register the new app |
| `docs/ai/CURRENT_STATE.md`, `DECISIONS_LOG.md` | Modified | Project convention |
| `backend/apps/uml_modeling/domain/` | Untouched | No new UML metadata needed |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Existing stored models have multi-parent generalization | Low | New rule is ERROR at validation; mapper raises rather than silently losing a parent |
| `Multiplicity` unvalidated (`upper=None`, `0..0`) edge cases | Med | Mapper defines explicit behavior per case, property-tested |
| Single Table produces wide, mostly-nullable tables | Med | Accepted tradeoff; subclass columns nullable by construction |
| Native `ENUM` is hard to alter later | Med | Regeneration-time concern only; no live DB in this cycle |
| Future generator reuses Django/Python idioms (§22 forbids) | Low | RelationalModel stays stack-neutral, no Django imports |

## Rollback Plan

Delete `backend/apps/relational_mapping/`, revert its `INSTALLED_APPS` entry, and revert the validation rule commit. No migrations, no schema, no persisted data — the module is pure and nothing else imports it.

## Dependencies

- `backend/apps/uml_modeling/domain/` `CanonicalUmlModel` (exists, stable).
- No new runtime packages.

## Success Criteria

- [ ] `map_to_relational` is deterministic: same model → identical `RelationalModel`.
- [ ] Each §21 rule (class, attribute, PK, 1:1, 1:N, N:M, composition, inheritance, enum, nullability, constraints) has a passing test.
- [ ] Multi-parent generalization produces an ERROR diagnostic and is refused by the mapper.
- [ ] Zero Django/DB/Java imports in the new domain module.
- [ ] `cd backend && pytest` green; change stays within the 800-line review budget.
