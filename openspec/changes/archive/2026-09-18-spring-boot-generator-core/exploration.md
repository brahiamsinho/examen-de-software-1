# Exploration: Spring Boot backend generator — first slice (spec §22, item 12 of §37)

## Current State

- Spec authority: `product-04-next-django.md` §22 (Backend generado) mandates
  the generated-backend stack unconditionally: Java 21 LTS, Spring Boot 4.x,
  Gradle, Spring Web MVC, Spring Data JPA, Hibernate, Jakarta Validation,
  Jackson, springdoc-openapi, PostgreSQL — layout
  `domain/persistence/application/api/validation/errors/config`. Generation
  mechanism is fixed: **Jinja2 + LibCST**; manual string-concatenation of
  source is explicitly prohibited. "El stack de la aplicación principal y el
  stack generado son conceptos independientes" — the generated stack must
  never be substituted for Modelia's own Django stack.
- §23 (Capacidades generadas): per entity, when applicable —
  create/read/update/delete/list/pagination/sorting/filtering/search/count/
  relation navigation. Natural-language operation resolution must come from
  structural metadata, not endpoints hand-coded phrase-by-phrase. No concrete
  routes/bodies fixed by the spec.
- §25 (OpenAPI + Postman): flow is `Backend generado -> OpenAPI -> Postman
  Collection -> typed frontend client (when applicable)`. §22 already fixes
  springdoc-openapi as mandatory in the generated stack, consistent with
  OpenAPI sourced FROM the generated backend. However §25's prose literally
  says "La especificación se generará mediante: OpenAPI nativo de Django
  Ninja" — this contradicts the springdoc-openapi requirement and the
  diagram's own direction. Flagged as a genuine spec ambiguity, not resolved
  by inference. Does not block this change (OpenAPI is item 14, not 12).
- §33 (Metadatos de generación): a "perfil propio" (`entity`, `auditable`,
  `readOnly`, `searchable`, `crud`, `required`, `unique`, `sortable`,
  `defaultSort`) controls persistence/frontend/search/audit/validation/
  assistant behavior. `CanonicalUmlModel.generation_metadata:
  Mapping[ElementId, Mapping[str, object]]` already exists in
  `backend/apps/uml_modeling/domain/model.py`, opaque and empty by default.
  Confirmed via grep it is round-tripped by `apps/uml_documents/codec.py` but
  consumed nowhere — no generation-capability logic reads it anywhere today.
- §34 (Testing > Generadores): explicitly requires generator tests to verify
  "archivos; sintaxis; compilación; relaciones; OpenAPI; Postman; Domain
  Manifest; frontend; backend; comandos del asistente" — **compilation is a
  required, spec-mandated test dimension**, not optional, but belongs to
  item 13, not this change.
- §37 (implementation order) and `docs/ai/CURRENT_STATE.md`'s Pending list
  agree exactly: 11 `UML -> RelationalModel` (done, archived
  `2026-09-18-uml-relational-mapping`), 12 `Spring Boot backend generator`,
  13 `generated backend compilable`, 14 `OpenAPI`, 15 `Postman`, 16 `Domain
  Manifest` — item 12 and item 13 are explicitly two separate ordered steps.
- `CanonicalUmlModel` (`backend/apps/uml_modeling/domain/model.py`,
  `elements.py`): `UmlOperation` (`id`, `name`, `return_type`,
  `parameters: tuple[UmlParameter, ...] = ()`, `visibility`) exists on every
  `UmlClass`, but per CURRENT_STATE.md Cycle 14, `parameters` is
  UI-unreachable in v1 (`UmlOperationIn` wire schema has no `parameters`
  field; the command handler always constructs `parameters=()`). Confirms
  §23's natural-language capability resolution is metadata-driven, not
  derived from `UmlOperation` names/signatures — consistent with what this
  session already told the user in the operations-feature cycle.
- `RelationalModel` (`backend/apps/relational_mapping/domain/schema.py`,
  produced by `mapping/mapper.py::map_to_relational`) is the actual,
  already-built input this generator will consume: `RelationalModel(tables,
  enum_types)`, `Table(name, columns, primary_key, foreign_keys,
  unique_constraints, indexes, source_class_ids, discriminator_column,
  discriminator_values)`, `Column(name, type: ColumnType, nullable, length,
  precision, scale, enum_type_name, source_element_id)`, `PrimaryKey`,
  `ForeignKey(on_delete, on_update, ...)`, `UniqueConstraint`, `Index`,
  `EnumType(name, labels, source_enumeration_id)`. Every table has an
  unconditional synthetic UUID PK named `id`; Single Table inheritance uses
  a `class_type` discriminator; enums are native-PostgreSQL-`ENUM`-flavored.
  Clean, complete, already-tested (442/442 backend tests as of the prior
  cycle) contract — no gaps found blocking a generator from consuming it
  directly.
- Toolchain check (repo-wide, case-insensitive grep): `jinja2`/`libcst`
  appear ONLY in `product-04-next-django.md`, `docs/ai/ARCHITECTURE.md`,
  `docs/ai/TECH_STACK.md`, and the archived `uml-relational-mapping`
  change's own docs (forward-looking mentions) — zero actual
  usage/dependency in `backend/requirements/*` or code. No Java, Gradle,
  `.java`, `build.gradle`, or `pom.xml` anywhere. No `.github/workflows/`
  directory exists at all — no CI pipeline of any kind today.
- `docker-compose.yml`: five services — `db` (Postgres 16, Modelia's own
  multi-tenant schema), `redis`, `backend` (Django/Daphne), `mailpit`,
  `frontend`. No JVM service, no second Postgres, no generated-project
  runner. `backend/Dockerfile` is a two-stage (`dev`/`prod`) pure-Python
  image — structurally incompatible with hosting a JVM/Gradle build without
  a new target or separate service/image.
- Session-confirmed, out-of-scope-for-this-change constraint: mobile/frontend
  generation (spec §26) is explicitly deferred — the user's eventual plan is
  a Flutter client pointing at the generated backend, but "eso lo dejamos pa
  después." The one constraint that DOES carry forward from that
  conversation: the generated backend must be externally configurable
  (no hardcoded host/port/URLs in generated templates), since it will
  eventually be deployed to the cloud and consumed by a mobile client that
  is not part of this change. This is a template-authoring constraint, not
  a design fork — Spring Boot's externalized `application.yml` + env var
  profile is the standard way to satisfy it.

## Affected/New Areas

- New Django app (per this project's one-app-per-domain convention, e.g.
  `backend/apps/backend_generator/`) — Jinja2 templates + LibCST-based
  emission, reading `RelationalModel` (and, for capability/audit logic,
  `CanonicalUmlModel.generation_metadata`) as pure input, producing a tree
  of generated source (in-memory/temp-dir) as pure output. Mirrors
  `relational_mapping`'s DB-free style.
- `backend/requirements/*.txt` — first real new dependencies this cycle:
  `jinja2`, `libcst` (both pure-Python, install cleanly in
  `python:3.12-slim`).
- `backend/apps/relational_mapping/domain/schema.py` — read-only primary
  input; no gaps found requiring changes.
- `backend/apps/uml_modeling/domain/model.py` (`generation_metadata`) —
  read-only IF the first slice honors per-entity capability metadata;
  otherwise untouched, every entity defaults to full CRUD (see Open
  Question 3).
- Untouched, confirmed: `docker-compose.yml`, `backend/Dockerfile`, any CI —
  deliberately a downstream, separately-decided concern (Open Question 1),
  not recommended for this slice.
- Explicitly out of scope per this session's decisions: frontend/mobile
  generation (§26, Flutter or otherwise), Domain Manifest (§28),
  assistant/AssistantCommand pipeline (§29-32).

## Approaches

1. **Pure "generator core" module first: `RelationalModel -> in-memory
   generated Java source tree`, Jinja2 + LibCST, unit-tested by rendering +
   structural parsing — no compilation, no Gradle invocation, no Docker/CI
   change.**
   - Pros: matches this project's proven "pure domain/module first" pattern
     (Cycle 1, `uml-relational-mapping`); isolates real design forks
     (template strategy, capability defaults, naming/package conventions)
     in one reviewable artifact; adds exactly two new pure-Python
     dependencies; zero new infra; fits the review budget if scoped
     narrowly.
   - Cons: no proof emitted Java actually compiles yet (explicitly deferred
     to spec item 13, a later cycle) — a real, spec-acknowledged
     intermediate state.
   - Effort: Medium.

2. **Generator core + a real compilation/verification step in the same
   change (bundles item 12 and item 13).**
   - Pros: proves the toolchain end-to-end sooner; satisfies §34's
     "compilación" requirement immediately.
   - Cons: requires deciding and standing up the containerization/CI answer
     (Open Question 1) BEFORE any template work can be validated; bundles a
     large infra decision with a large codegen decision; contradicts §37's
     explicit 12-before-13 ordering; very likely exceeds the review budget.
   - Effort: High.

3. **Full §22-25 in one change: generator + compilation + OpenAPI + Postman
   collection.**
   - Pros: none beyond fewer PRs.
   - Cons: mixes four different risk profiles (codegen, JVM build, OpenAPI
     extraction, Postman derivation) in one review; direct violation of the
     spec's own ordering (12/13/14/15); certain to exceed the review
     budget.
   - Effort: Very High.

## Recommendation

Approach 1 — a standalone, pure "generator core" module (`RelationalModel ->
in-memory/temp-dir Java source tree` via Jinja2 templates + LibCST-assisted
assembly), unit-tested by rendering + structurally validating output (file
paths under the required
`domain/persistence/application/api/validation/errors/config` layout;
syntactic sanity checks on emitted `.java` text — NOT `javac`/Gradle). No
Docker/CI change, no compilation proof, no OpenAPI/Postman work. Direct
sequel to how `uml-relational-mapping` was scoped, keeps item 12 cleanly
separate from item 13 exactly as §37 orders them.

Recommend narrowing further within item 12 for the very first change: **one
entity, one simple relational shape (PK + a few scalar columns, no
FK/join-table/discriminator yet), through `domain/`+`persistence/` layers
only** — proving the Jinja2+LibCST pipeline and file-layout convention on
the smallest slice, with `application/api/validation/errors/config` and
relationship/inheritance/enum-aware templates as explicit follow-up cycles.
Mirrors relational-mapping's own internal staging rather than attempting all
six directories and every `RelationalModel` shape in one pass.

## Risks

- §25's literal text ("OpenAPI nativo de Django Ninja") contradicts §22's
  mandatory `springdoc-openapi` and the flow diagram's own direction.
  Doesn't block this change (OpenAPI is item 14, not 12) but should be
  raised before that later cycle.
- §33's generation-metadata profile has zero consumers today; if slice 1
  defaults every entity to "full CRUD, no capability gating," that default
  must be explicit and documented, since §23 conditions capabilities on
  "cuando corresponda."
- The generated backend's stack (Java/Gradle) has no host anywhere in this
  repo's Docker/CI today — deferring this is deliberate (Approach 1), but
  item 13 will need its own infra decision before it can start.
- LibCST is a Python-specific CST library; pairing it with Jinja2 for Java
  generation likely means LibCST governs the *generator's own Python
  source* (no manual string concatenation when assembling/writing
  templates), not that it parses the emitted Java. This should be confirmed
  with the user before design — the two readings imply very different test
  strategies.
- No prior art in this repo for multi-language codegen testing (asserting
  "valid Java" without a JVM present) — needs an explicit, cheap validation
  method decided before implementation.

## Open Questions (for the user, before proposal)

1. **Containerization/deployment topology for the generated backend**
   (major — spec-acknowledged as item 13's concern, but shapes how far item
   12's design can go without rework): does Modelia ever run/compile a
   generated backend itself, or does the generator only emit source + a
   self-contained Dockerfile/docker-compose.yml as OUTPUT, run entirely
   outside Modelia's infra by the end user?
   (a) Modelia never runs generated code — "compilable" proof via a
   lightweight offline check or a manual maintainer-run JDK step;
   generator's job ends at emitting a working, self-contained Gradle
   project.
   (b) Modelia provisions an ephemeral container + fresh Postgres per
   generated project to literally compile/run it — needs a new
   Java/Gradle-capable image, a second Postgres instance, and orchestration
   added to `docker-compose.yml`/a to-be-created CI pipeline (none exists
   today).
   No existing infrastructure leans either way — genuinely open, not
   inferable from the codebase.
2. **Jinja2 + LibCST division of labor**: confirm whether LibCST operates
   on the *generator's own Python source* (avoiding manual string
   concatenation) or is expected to parse/manipulate the *emitted Java*
   output. Changes what "verified" means for generated files and what
   slice 1's tests must assert.
3. **Generation-metadata defaults for slice 1**: hard-code "every entity
   gets full create/read/update/delete/list" (deferring §33's
   `crud`/`readOnly`/etc. profile to a later cycle alongside the Domain
   Manifest, item 16), or must even slice 1 honor a minimal per-entity
   capability toggle from `CanonicalUmlModel.generation_metadata`?
4. **"Compilable" verification method for item 13** (not this change, but
   shapes whether item 12's file-layout choices need to anticipate it):
   local JDK on the maintainer's machine only, a to-be-created CI workflow
   with a JDK, or the containerized ephemeral-build approach from Question
   1?
5. **Scope boundary of the very first change within item 12**: agree with
   narrowing to "one entity, `domain/`+`persistence/` layers only, no
   relationships/inheritance/enums yet" (this exploration's recommendation),
   or is a wider first slice preferred?

## Ready for Proposal

No — Open Questions 1-3 need explicit user resolution before `sdd-propose`;
they are genuine, unresolved design forks (not spec-mandated, not
inferable from existing code/infra), and each materially changes proposal
scope. Question 4 can be deferred (belongs to item 13, a later cycle) but is
worth surfacing now as the natural follow-on to Question 1. Question 5 can
default to this exploration's recommendation if the user has no objection,
but should be confirmed, not silently assumed, since it sets the
review-budget-sized scope of the next `sdd-propose`.
