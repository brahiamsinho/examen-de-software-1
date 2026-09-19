# Exploration: Spring Boot generator — application/ (service) + api/ (REST controller) layers for CRUD capabilities (spec §22/§23)

## Current State

- Two archived cycles built `backend/apps/spring_generator/`: `generate_table_sources(table, *,
  base_package) -> GeneratedSources` (one JPA `@Entity` in `domain/` + one Spring Data repository
  interface in `persistence/`, now handling scalar columns, FK relationships as
  `@ManyToOne`/`@OneToOne` + `@JoinColumn`, and enum columns as `@Enumerated(EnumType.STRING)`)
  and `generate_enum_source(enum_type, *, base_package) -> GeneratedFile` (standalone Java enum in
  `domain/`). Both are pure functions of a single `Table`/`EnumType`, never touching
  `relational_mapping.validate()` or a DB.
- `Repository.java.j2` is minimal today: `public interface {{repository_name}} extends
  JpaRepository<{{class_name}}, UUID> { }` — zero custom query methods. `JpaRepository<T,ID>`
  already extends `PagingAndSortingRepository`/`CrudRepository`, so `findAll(Pageable)` (returns
  `Page<T>`, gives pagination+sorting for free), `findAll(Sort)`, `count()`, `save`, `findById`,
  `deleteById` are all already available with **no repository-interface change needed**.
- `emit/context.py::_relationship_field_context` types FK fields as the **related entity's Java
  class** (`@ManyToOne private Customer customer;`), not as a raw UUID, and never sets `fetch =
  FetchType.LAZY`. JPA's default fetch type for `@ManyToOne`/`@OneToOne` is EAGER. Confirmed
  technical fact: serializing the entity directly over Jackson would eagerly embed the full
  related entity's fields, not just its id — a concrete defect if this slice exposes entities
  directly in REST responses, not a hypothetical.
- Jakarta Validation annotations (`@NotNull`, `@Size`) already live directly on entity fields
  (built in `context.py`), not on a separate DTO. §22's mandatory 6-dir layout
  (`domain/persistence/application/api/validation/errors/config`) — `validation/`, `errors/`,
  `config/`, `application/`, `api/` are untouched by both archived cycles.
- `relational_mapping.domain.schema` (`Column`, `Table`, `ForeignKey`, `EnumType`,
  `RelationalModel`) has **no fields for §33's own metadata concepts** (`entity`, `auditable`,
  `readOnly`, `searchable`, `crud`, `required`, `unique`, `sortable`, `defaultSort`) —
  structurally identical gap to the inheritance-owning-class gap the previous exploration
  flagged. §23's "cuando corresponda" (filtering/search specifically) cannot yet be gated by real
  metadata.
- §27's type→UI table (`product-04-next-django.md` §27) expects flat scalar FK ids for N:1 fields
  (`select/autocomplete`), reinforcing that a REST response embedding the full nested related
  entity mismatches what a generated frontend will consume.
- No compilation/build verification of generated Java exists yet anywhere in the repo (roadmap
  item 13, "Backend generado compilable" — separate/later); all existing spring_generator tests
  assert on generated Java TEXT only.
- §23 requires natural-language operations to resolve from structural metadata, not parsed UML
  operation names — this constraint still holds and is untouched by this exploration.

## Affected Areas

- `backend/apps/spring_generator/emit/renderer.py` — new render path(s)/function(s) for service
  class + REST controller, sibling to `generate_table_sources`.
- `backend/apps/spring_generator/emit/context.py` — new `build_service_context`/
  `build_controller_context`, covering CRUD/pagination/sorting/count endpoint signatures.
- `backend/apps/spring_generator/emit/templates/` — new `Service.java.j2`, `Controller.java.j2`,
  and a minimal `@ControllerAdvice` template for `errors/`.
- `backend/apps/spring_generator/emit/errors.py` — likely unaffected for this slice's happy path.
- `backend/apps/spring_generator/tests/` — new test files mirroring
  `test_entity_structure.py`/`test_repository.py` for the new layers.
- `docs/ai/CURRENT_STATE.md`, `NEXT_STEPS.md`, `DECISIONS_LOG.md` — updated per `AGENTS.md`'s
  memory convention once a slice lands.

## Approaches

1. **Entity-direct exposure, minimal CRUD only** — no DTOs, no filtering, no search.
   - Pros: smallest possible slice; reuses `@NotNull`/`@Size` already on the entity for `@Valid`.
   - Cons: response bodies eagerly embed full nested related entities (confirmed EAGER default) —
     mismatches §27's flat-FK-id UI expectation; still 500s on not-found; misses filtering,
     search, and explicit relation-navigation.
   - Effort: Low.

2. **Full §23 capability set now** — generic `Specification`-based filtering + search across all
   scalar columns, explicit relation-navigation sub-resource endpoints
   (`GET /parent/{id}/children`), entity-direct exposure.
   - Pros: closes every §23 bullet in one slice.
   - Cons: relation-navigation as a sub-resource needs the INVERSE FK direction (which OTHER
     tables have a FK pointing AT this table) — not derivable from a single `Table` alone;
     requires the whole `RelationalModel`, a real API-shape change beyond
     `generate_table_sources(table)`'s one-Table-at-a-time signature; Specification-based generic
     filtering is substantial new template complexity; breaks the established precedent of
     narrow, additive cycles.
   - Effort: High.

3. **CRUD + pagination + sorting + count now** (all deterministically derivable from
   `JpaRepository`'s inherited behavior, zero §33-metadata dependency, zero cross-table
   awareness), **flat FK-id response representation** instead of nested entities, **minimal
   `errors/` handler** for not-found/validation — defer filtering, search, and
   relation-navigation-as-sub-resource to a later slice.
   - Pros: every included capability is deterministically derivable from one `Table` today,
     consistent with Generator Purity and the one-Table-at-a-time precedent; sidesteps the
     not-yet-existing §33 metadata dependency entirely; fixes the EAGER-serialization defect as
     part of the same slice instead of shipping it broken; meaningfully expands generated
     capability (2 new §22 directories) without the two genuinely-blocked capabilities.
   - Cons: doesn't close §23 in one shot; flat-relationship representation is itself a smaller
     open decision (raw UUID field vs. minimal `{id}` object) that still needs confirming; a
     "minimal errors/ handler" edges slightly outside a strict "just application/+api/" framing.
   - Effort: Medium.

## Recommendation

Approach 3: `application/` (service) + `api/` (REST controller) generation for
create/read/update/delete/list/pagination/sorting/count, using `JpaRepository`'s inherited
paging/sorting/count contract with NO repository-interface change, flat FK-id representation in
request/response bodies (fixing the confirmed EAGER-embed defect), plus a minimal `errors/`
`@ControllerAdvice` mapping not-found/validation to 404/400. Filtering, search, and
relation-navigation-as-sub-resource are deferred to a later slice. This mirrors both archived
cycles' pattern of picking the deterministic, low-ambiguity subset first.

## Risks

- EAGER-fetch + entity-direct-serialization is a confirmed technical defect if flattening/DTOs
  are skipped (verified via `Entity.java.j2`/`context.py`: no `fetch = LAZY` override, no
  `@JsonIgnore`).
- §33 metadata (`searchable`, `sortable`, etc.) does not exist in `relational_mapping.domain.schema`
  yet — filtering/search cannot be metadata-gated until an upstream schema change lands.
- Relation-navigation as nested sub-resource endpoints needs the whole `RelationalModel`, not one
  `Table` — the same shape of scope creep already flagged and deferred in the relationships/enums
  cycle for bidirectional `@OneToMany`.
- Not-found handling: relying on `JpaRepository`'s inherited `findById`/`deleteById` alone is not
  sufficient for a clean 404 — the generated service layer needs to explicitly check
  `.isPresent()` / throw a typed not-found exception; an `sdd-design` detail, not resolved here.
- No compilation verification exists yet for any previously generated Java source (roadmap item
  13 is separate/future work); this slice's generated service/controller Java text will only be
  tested via text assertions.

## Open Questions (for the user, before proposal)

1. **BLOCKING.** Entity-direct exposure vs. a thin flattening/DTO step for relationship fields.
   Given the confirmed EAGER-fetch nested-entity serialization issue, does this slice flatten
   relationship fields to a raw FK UUID in the response (recommended — cheap, deterministic
   per-`Table` transform, fixes an already-discovered defect) or accept the nested-entity shape
   for now and defer to a later slice?
2. **BLOCKING for filtering/search scope only**: should this slice add generic
   `Specification`-based filtering/search across all scalar columns with no §33 metadata gate, or
   wait for a §33 metadata schema extension so filtering/search can be scoped to the fields the
   metadata actually names? Recommend deferring to a later slice (already assumed by Approach 3).
3. **BLOCKING for relation-navigation scope only**: does §23's "navegación de relaciones" mean
   (a) the FK id already present in the entity/response — satisfied by Approach 3's flat FK
   representation, no new endpoint — or (b) an explicit nested sub-resource endpoint (`GET
   /parent/{id}/children`) requiring whole-`RelationalModel` awareness (a real API-shape change)?
   Recommend (a) for this slice.
4. Non-blocking, low-priority: keep the minimal `errors/` `@ControllerAdvice` in this slice's
   scope (recommended — small, deterministic, 2 exception-to-status mappings) or defer it
   alongside `config/` to its own later slice?
5. Non-blocking: does `Repository.java.j2` need to start declaring
   `PagingAndSortingRepository`/`JpaSpecificationExecutor` explicitly, or does the already-
   generated `JpaRepository<T, ID>` (already transitively provides `findAll(Pageable)`/
   `findAll(Sort)`/`count()`) stay unchanged for this slice's scope? Recommend no
   repository-interface change now; revisit only if/when Specification-based filtering (Open
   Question 2) is added later.

## Ready for Proposal

No — Open Questions 1, 2, and 3 need explicit user resolution before `sdd-propose`. Question 4
defaults to "in scope" and Question 5 defaults to "no repository change" if not raised
explicitly, consistent with this exploration's Approach 3 recommendation.
