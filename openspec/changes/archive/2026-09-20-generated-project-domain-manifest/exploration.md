# Exploration: generated-project-domain-manifest

Spec `product-04-next-django.md` §28 and §37 item 16. Engram: `sdd/generated-project-domain-manifest/explore` (obs 716).

## What the spec requires

- §28 (L898-916): "Se generara un `Domain Manifest` derivado del modelo y/o OpenAPI." Content: entities, attributes, types, relationships, aliases, searchable properties, sortable properties, allowed operations, validations, CRUD capabilities, and the logical mapping the executor needs. The spec deliberately includes no JSON example, so the schema is ours (carry a `schemaVersion`).
- Consumers: §29 (in-app assistant: ONNX + Domain Manifest -> AssistantCommand -> CommandValidator -> Executor; it may only operate declared capabilities), §26/§27 (generated frontend CRUD inference), §34 (generator tests must verify the manifest), `docs/ai/ARCHITECTURE.md` L178.
- §33 (L1008-1033) own-profile metadata (entity, auditable, readOnly, searchable, crud, required, unique, sortable, defaultSort) is NOT available anywhere yet: `CanonicalUmlModel.generation_metadata` is an opaque mapping the codec persists and `map_to_relational` never reads.
- Main spec constraint: `openspec/specs/spring-boot-generation/spec.md` (L600, L609) says `generate_model_sources` and the aggregate MUST NOT add a Manifest. The 41-file oracle is pinned in `generation_runner/tests/test_sample_model.py`, `generation_runner/tests/test_cli.py` and `spring_generator/tests/test_project_sources.py`.

## Current state (evidence)

- `RelationalModel` has frozen `Table`, `Column`, `ForeignKey`, `EnumType`. Original UML names are lost (snake_case table/column names plus `discriminator_values`).
- Generated API per non-inheritance table: POST "", GET /{id}, PUT /{id}, DELETE /{id}, GET "" (Pageable), GET /count under `/api/` + `resource_path_segment(table.name)`. Inheritance tables get entities + repository only (no controller/DTO/service). The committed OpenAPI fixture (`backend/apps/postman_export/tests/fixtures/api-docs.json`) has exactly 5 paths: customers, purchases, products, tags, product-tags.
- Validations: `@NotNull` when not nullable, `@Size(max=length)` for VARCHAR. API field names `camel_case(column.name)`, entity classes `pascal_case(table.name)`.
- Conventions to mirror (`postman_export`, DD109-DD120): pure package + `cli.py` + `apps.py`, INSTALLED_APPS, plain `__main__` without `django.setup`, fixed filenames, dump indent=2/sort_keys/ensure_ascii=False/trailing newline/newline="\n", compose service in profile `jvm-verify` without `depends_on` and `rm -rf`, literal command array, gate step after the smoke.

## Approaches

| Approach | Pros | Cons | Effort |
|---|---|---|---|
| A. Derive from RelationalModel; new app `apps.domain_manifest`; output `docs/domain-manifest.json` | Pure, deterministic, reuses `spring_generator.emit.naming` (no drift), knows hierarchies have no endpoints, can absorb `generation_metadata` later, leaves the 41-file oracle and its spec untouched | Endpoints computed, not read from springdoc (mitigate with a pytest cross-check against the committed fixture) | Medium |
| B. Derive from captured `docs/openapi.json` | Reflects served contract | No relationship/inheritance/alias/§33 semantics, heuristic parsing, depends on the smoke export | Medium |
| C. Emit as a `GeneratedFile` in `generate_project_sources` | Ships inside the project | Amends main spec, changes the 41-file oracle in 4+ test files | High |
| D. A + B | Strongest proof | More code, more complex gate | High |

## Recommendation: A

- Source of truth: the RelationalModel. The earlier rejection of deriving OpenAPI from the relational model does not apply (a manifest is not the API contract; springdoc stays the only OpenAPI producer). One drift guard: pytest asserts the manifest's resource paths for the sample model equal the paths in the committed `api-docs.json` fixture.
- Location: new app `apps.domain_manifest`, sibling of `postman_export` (pure `builder/`, serialize, `cli.py`, `apps.py`, no models/migrations, registered after `postman_export`). One-way import of `spring_generator.emit.naming` (pure functions); CLI glue imports `generation_runner.samples.sample_model`. Duplicate the ~15-line serialize instead of importing from `postman_export` (DD109 decoupling rationale; confirm at design).
- Emission: `python -m apps.domain_manifest.cli --out-dir /generated/project/docs` writes `domain-manifest.json`. Compose service `generate-manifest` (profile `jvm-verify`, no `depends_on`, no `rm -rf`, literal command) and gate step 4 after `generate-postman` with a new exit code.
- Proof: pytest proves builder and CLI (subprocess without `django.setup`, fixed filename, byte-identical two runs, fixture path cross-check, decoupling). Compose and script are proven by the manual gate plus gate-evidence and one negative check (DD101/DD120).
- Minimal manifest, `schemaVersion: 1`: `entities[]` (name, table, resourcePath, `operations[]` {name, method, path} with the 6 CRUD operations or empty for inheritance roots, `attributes[]` {name, column, type, required, maxLength, enum, primaryKey}, `relationships[]` {field, kind, target, required}, subtypes, uniqueConstraints) and `enums[]` {name, values}. Do NOT fake searchable/sortable/defaultSort/auditable/readOnly/aliases: document them as a follow-up that needs the mapper to carry `generation_metadata`, and record the UML vs own-profile split note §33 requires.

## Size and split

About 250 production lines, tests 350-450, compose/script ~25, docs ~60: 700-850 total; no large fixture needed. One slice; if tests push past 800, split into slice 1 (builder + CLI + pytest) and slice 2 (compose + gate step + evidence + docs).

## Risks

- Endpoint drift (computed, not read from springdoc): the fixture cross-check guards it.
- No spec contract for the JSON shape: hence `schemaVersion`.
- If an inheritance API is added later, the builder must follow (single naming source mitigates).
- The CLI supports only the sample model, like the `generation_runner` CLI; real-project input is future work.
- The `spring_generator.emit.naming` dependency needs a decoupling test allowing only that import.

## Non-goals

`generation_metadata`/§33 schema and aliases, filtering/search API, frontend/mobile generation, the assistant/AssistantCommand, auth, embedding the manifest in the Spring project, deriving it from OpenAPI.

## Product decisions needing the user

None blocking. Defaults: (1) emit only what is declared or generated today, no fake searchable/sortable; (2) manifest lives at `docs/domain-manifest.json` in the `generated_project` volume via a separate CLI, not in the 41-file Spring tree; (3) aliases deferred.
