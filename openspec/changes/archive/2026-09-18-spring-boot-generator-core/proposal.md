# Proposal: Spring Boot generator core — first slice (§22, item 12)

## Intent

Item 11 (`UML -> RelationalModel`) is done; `RelationalModel` is a clean, tested,
gap-free input with no consumer. Item 12 (§37) turns it into generated Spring Boot
source. This change proves the spec-mandated Jinja2 + LibCST pipeline and the §22
package layout on the smallest honest slice — one table, `domain/` + `persistence/`
only — so template strategy, naming and package conventions are settled in one
reviewable artifact before relationships, further layers, or compilation (item 13).

## Confirmed Decisions (settled constraints, not open forks)

| # | Decision |
|---|---|
| D1 | Modelia will eventually provision an ephemeral JVM/Gradle container + fresh PostgreSQL to compile/run generated backends, orchestrated via `docker-compose.yml` or a future CI pipeline. Forward-looking direction for item 13 — **not built here**. |
| D2 | LibCST governs the generator's own Python source (assembling template-driving code, no manual string concatenation). It does **not** parse emitted Java. Tests assert emitted `.java` structurally: expected paths, class/field names, brace balance. No `javac`, no Java parser. |
| D3 | Full CRUD (create/read/update/delete/list) is hard-coded for every entity. `CanonicalUmlModel.generation_metadata` (§33 profile) is **not** consumed; deferred to item 16. |
| D4 | One table at a time, `domain/` + `persistence/` only: JPA `@Entity` class + Spring Data JPA repository interface. No relationships, inheritance/discriminator, or enum types. |

## Scope

### In Scope
- New Django app `backend/apps/spring_generator/` (no collision; app-per-domain convention), DB-free like `relational_mapping`.
- Pure function: `Table` (scalar columns, synthetic UUID PK, no FK/discriminator/enum) -> Java source text for entity + repository, in-memory or temp dir.
- Jinja2 templates under the §22 `domain/persistence/...` path layout; Java 21, Spring Data JPA, Hibernate, Jakarta Validation, Jackson annotations as applicable.
- No hardcoded host/port/URL in any template (externalized-configuration constraint).
- `jinja2` + `libcst` added to `backend/requirements/*.txt`.
- TDD unit tests per D2.

### Out of Scope
- Relationships/FK, inheritance/discriminator, enum type generation.
- `application/`, `api/`, `validation/`, `errors/`, `config/` layers.
- Compilation, Gradle invocation, `javac` (item 13).
- Any Docker, CI, or container work.
- OpenAPI (14), Postman (15), Domain Manifest (16).
- Frontend/mobile generation (§26, Flutter or otherwise).

## Capabilities

### New Capabilities
- `spring-boot-generation`: deterministic emission of Java source for a relational table's domain entity and persistence repository.

### Modified Capabilities
- None.

## Approach

Exploration Approach 1, narrowed per D4. `RelationalModel` stays a read-only input;
the generator is a pure module (input -> source tree), mirroring `relational_mapping`.
Jinja2 owns Java text; LibCST owns the generator's Python assembly (D2).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/apps/spring_generator/` | New | Templates, emitter, tests |
| `backend/requirements/*.txt` | Modified | `jinja2`, `libcst` |
| `backend/apps/relational_mapping/domain/schema.py` | Read-only | Input contract, unchanged |
| `config/settings` `INSTALLED_APPS` | Modified | Register new app |
| `docs/ai/CURRENT_STATE.md`, `DECISIONS_LOG.md` | Modified | Project convention |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| §25 says "OpenAPI nativo de Django Ninja", contradicting §22's mandatory springdoc-openapi | High | Spec ambiguity; raise before item 14. Does not block this change |
| §33 metadata ignored, but §23 says capabilities apply "cuando corresponda" | Med | D3 makes the full-CRUD default explicit and documented as tech debt |
| Structural-only assertions cannot prove the Java compiles | High | Accepted and spec-ordered (12 before 13); item 13 owns compilation |
| Item 13 has no JVM host anywhere in repo infra today | High | D1 records the intended direction; decided in its own cycle |
| Naming/package conventions chosen now may need rework at wider slices | Med | Slice is deliberately small and cheap to revise |

## Rollback Plan

Delete `backend/apps/spring_generator/`, revert its `INSTALLED_APPS` entry and the two
requirements lines. Nothing else imports it and no migrations exist, so removal is total.

## Dependencies

- `jinja2`, `libcst` (pure Python, install cleanly in `python:3.12-slim`).
- `relational_mapping.domain.schema` (already merged).

## Success Criteria

- [ ] A `Table` with scalar columns + UUID PK yields an `@Entity` class and a Spring Data JPA repository at §22-conformant paths.
- [ ] Tests assert paths, class/field names, and brace balance — no `javac`.
- [ ] No manual string concatenation builds generator source; no hardcoded host/port/URL in templates.
- [ ] `cd backend && pytest` green; change stays within the 800-line review budget.
