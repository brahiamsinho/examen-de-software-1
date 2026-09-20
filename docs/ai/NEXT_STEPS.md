# Next Steps

**Update 2026-09-20 (newest):** `2026-09-20-generated-spring-api-filtering-search` is verified (PASS), archived, uncommitted (20/20 tasks, Strict TDD; `apps/spring_generator` 354 passed, Docker backend 1214 passed, frontend 351 passed). New generator capabilities: `JpaSpecificationExecutor` for searchable tables, `Specifications` builder templates, controller filter query params (string LIKE, numeric eq), sort validation with 400, `defaultSort` fallback. Next: commit normally excluding `.pi/`, then address DD147 (`crud` restricts `operations[]`) or continue with deferred inheritance API / relationship-navigation slices.

Updated 2026-09-20. For the full picture read `HANDOFF_LATEST.md` first. Spec
section 37 (`product-04-next-django.md`) fixes the implementation order; items
1–6, 8, 9, 11, 13, 14, 15 and 16 are done and archived, item 12 is partial.

## Where we are

**Update 2026-09-20 (previous dependency):** `uml-generation-profile-authoring` is applied, verify pending, uncommitted (31/31 tasks, Strict TDD, backend 1107 -> 1184 passed, `apps/uml_commands` 86, `apps/uml_documents` 134, ~1208 authored lines, `size:exception` accepted; DD151-DD159). The frontend follow-up `2026-09-20-uml-generation-profile-panel` is now verified and archived. After committing the archived frontend slice, continue in order: (1) filtering/search in the generated Spring API using `searchable` / `sortable` / `defaultSort`; (2) make `crud` restrict `operations[]` in the manifest and the generator (DD147 tech debt); (3) §37 item 12 remainder (inheritance DTOs/services/controllers, relation-navigation endpoints); (4) Flutter frontend (§37 item 17).

**Update 2026-09-20 (previous):** `manifest-generation-profile` is verified (PASS WITH WARNINGS, 0 critical) and archived, committed as `cdae44c` (24/24 tasks, Strict TDD, `apps/domain_manifest` 125 passed (88 before), backend 1107 passed (1070 before), ~419 authored lines, no `size:exception` needed; delta merged into `openspec/specs/domain-manifest-export/spec.md`, now 15 requirements, archived to `openspec/changes/archive/2026-09-20-manifest-generation-profile/`). Accepted warnings: M3 equivalent mutant (redundant `profile is None` guard); task 11.4 closed at archive; `EXCLUDED_KEYS` equality not asserted explicitly; the 'foreign id' scenario is covered by an id matching no column. Candidates listed at that time (the newest update supersedes this list): (1) filtering/search in the generated Spring API using `searchable` / `sortable` / `defaultSort`; (2) an authoring path for the profile in commands/UI; (3) make `crud` restrict `operations[]` in the manifest and the generator (DD147 tech debt); (4) §37 item 12 remainder (inheritance DTOs/services/controllers, relation-navigation endpoints); (5) Flutter frontend (§37 item 17).

**Update 2026-09-20 (previous):** `relational-generation-metadata` is verified (PASS WITH WARNINGS, 0 critical) and archived, committed as `284881e` (34/34 tasks, Strict TDD, backend 1070 passed, `apps/relational_mapping` 138, `apps/domain_manifest` 88; ~960 authored lines accepted as `size:exception`; delta specs `generation-profile` (new) and `relational-mapping` (modified) merged). Its follow-up (the Domain Manifest gaining the profile keys, with `defaultSort.attribute` resolved to a column) is done by `manifest-generation-profile` above; the remaining candidates are listed there. `required` / `unique` keys and `entity: false` semantics stay deferred.

**Update 2026-09-20 (previous):** `generated-project-domain-manifest` is verified (PASS WITH WARNINGS, 0 critical) and archived (31/31 tasks, Strict TDD, gate green with a fourth step, negative check exit 1 reverted, backend 987 tests) and committed as `d2069a5`. `size:exception` was accepted for its 811-line slice 1. Its follow-ups (mapper carrying `generation_metadata`, manifest emitting the profile) are done by the two changes above; the remaining candidates are listed in the newest update. Optional: import `postman_collection.json` into the Postman app.

**Update 2026-09-20 (later):** `generated-project-postman-collection` is verified PASS WITH WARNINGS, archived and committed as `8bb9fd0` (31/31 tasks, Strict TDD, gate green, backend 900 tests); delta specs `postman-collection-export` (new) and `generated-project-verification` (modified) merged. Optional: import `postman_collection.json` into the Postman application (not done yet).

**Update 2026-09-20:** `generated-project-openapi-springdoc` is verified PASS WITH WARNINGS
and archived (committed as `a834ca2`). The `/v3/api-docs` document it serves is what the
Postman change above consumes.

The Spring Boot generator (§37 item 12) has seven archived generator slices, all
text-only: `spring-boot-generator-core` (entity + repository),
`spring-boot-generator-relationships-enums` (FK relationships, enum fields,
standalone enum source), `spring-boot-generator-application-api-layer` (DTOs,
service, REST controller, shared error handling),
`2026-09-19-spring-boot-generator-inheritance` (discriminator-backed Single
Table domain classes plus one root repository only), and
`2026-09-19-spring-boot-generator-config-layer` (pure project-singleton
`src/main/resources/application.yml` only, six required no-default placeholders
including `JPA_DDL_AUTO`, no dialect/platform, no Java `config/` classes), and
`2026-09-19-spring-boot-whole-model-orchestrator` (pure in-memory
`generate_model_sources(...)` aggregation with exact duplicate-path rejection),
plus the archived `2026-09-19-spring-boot-project-scaffold` (pure
`build.gradle`/`settings.gradle`/`Application.java` scaffold and
`generate_project_sources(...)`, §37 item 13 slice 1 of 3). Slice 2
(`generated-project-compile-check`) is verified (PASS WITH WARNINGS) and archived, not yet
committed. The relational mapper has the archived
`relational-column-ownership` prerequisite: attribute-derived columns carry
`owning_class_id`; non-attribute columns keep `None`.

**Update (verified and archived):** the change
`spring-generator-inheritance-subclass-naming` is verified (PASS WITH WARNINGS, 0 CRITICAL) and
archived to `openspec/changes/archive/2026-09-19-spring-generator-inheritance-subclass-naming/`.
It fixes the former subclass-naming defect (`emit/inheritance_context.py:169` now uses
`pascal_case(table.discriminator_values[class_id])`), and the compile-check sample
model uses frozen uuid4-hex class ids. Delta spec is merged into the main
`openspec/specs/spring-boot-generation/spec.md`.

## Next candidates, in dependency order

1. **Design inheritance API behavior only if requested.** The archived
   inheritance slice intentionally stops at JPA Single Table domain entities
   plus the root repository. DTOs, services, controllers, subclass repositories,
   Java compilation and generation_metadata-based manifest fields remain future work (OpenAPI, Postman and the Domain Manifest exist at the project level).
2. **Broader generated backend configuration remains deferred.** The bounded
   `application.yml` singleton now exists with six required no-default
   placeholders only; Java `config/` classes, profiles, Docker/runtime
   scaffolding, and orchestration are still not started.
3. **Relationship navigation and bidirectional generation design** — the now-archived whole-model orchestrator unlocks future bidirectional `@OneToMany` and
   relation-navigation sub-endpoints, but those behaviors remain unimplemented
   and need their own SDD cycle.
4. **Filtering/search** — unblocked: the relational schema carries the §33
   generation profile (`relational-generation-metadata`) and the Domain Manifest
   emits it (`manifest-generation-profile`); the generated Spring API does not use it yet.
5. **§37 item 13, generated backend compilable — slice 2 of 3 verified and archived
   (uncommitted).** Slice 1 (`2026-09-19-spring-boot-project-scaffold`,
   archived) added the pure scaffold text. Slice 2 `generated-project-compile-check`
   is verified (PASS WITH WARNINGS) and archived: `apps/generation_runner/` (pure `write_sources`
   writer, CLI, sample model, image-tag function) plus the manual compose gate.
   To re-run the gate from the repo root in Git Bash:
   `bash scripts/verify-generated-project.sh` (expect `BUILD SUCCESSFUL`, exit 0).
   It is NOT part of `pytest` (DD85). Immediate next actions, in order:
   - **Commit slice 2** (nothing is committed yet; never commit `.pi/` or `.pi/*`).
   - W2 was fixed: CLI now catches `(GeneratedSourceWriteError, UngeneratableSourceError, ValueError, OSError)`
     with two added test cases in `tests/test_cli.py`; final counts: 822 backend tests (58 in `apps/generation_runner`).
   - **Slice 3 `generated-project-boot-smoke`**: verified (PASS WITH WARNINGS) and
     archived 2026-09-19 (18/18 tasks); §37 item 13 is now complete. The gate boots
     the jar against a throwaway Postgres and runs a CRUD round-trip; see
     `openspec/changes/archive/2026-09-19-generated-project-boot-smoke/gate-evidence.md`.
     (committed.)
   - Also deferred: Gradle wrapper (binary jar, `GeneratedFile.contents` is `str`),
     `.gitignore`, Dockerfile.
6. **§37 items 14–16** — OpenAPI, Postman collection, Domain Manifest (all done; 14, 15 and 16 archived).
   Resolved with the user (see `DECISIONS_LOG.md`): the generated Spring backend uses
   springdoc-openapi (§22 wins over §25); Django Ninja's OpenAPI stays for Modelia's
   own API. Springdoc is in the scaffold (`emit/versions.py`, Boot 4.1.1 confirmed) and the
   Postman collection is committed (`generated-project-postman-collection`); the Domain
   Manifest is archived (`generated-project-domain-manifest`, PASS WITH WARNINGS, committed as `d2069a5`).

## Explicitly deferred by the user

- Generated frontend/mobile (§26). The user plans Flutter instead of the
  spec's Next.js PWA + Capacitor ("that comes later"). Do not scope it in
  until they raise it.
- The existing `mobile/` Flutter app targets Modelia's own Django API for
  limited review/consult (spec line about mobile). Real screens under
  `mobile/lib/` are still to be built.

## Loose ends (low priority, do not chase unprompted)

- §37 items 7 (Undo/Redo) and 10 (Presence) have no dedicated archived cycle
  and are not verified as implemented.
- The user has not visually confirmed, in a browser, the operations
  compartment on class boxes or the aggregation/composition rendering.
- Cypress (E2E) bootstrap was never started.
- Decisions the generator carries as accepted tech debt: irregular English
  plurals in REST paths (`person` → `persons`), unquoted SQL reserved words in
  `@Table`/`@Column` names, `Page<T>` serialized directly, enum persisted value
  is the SCREAMING_SNAKE constant rather than the model's original label.
