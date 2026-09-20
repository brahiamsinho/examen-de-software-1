# Design: Generated Project Domain Manifest

## Technical Approach

One new app, `apps.domain_manifest`, mirroring the `postman_export` shell (pure package + `serialize.py` + plain `__main__` CLI + `apps.py`, no models, no migrations). A pure `builder/` turns the `RelationalModel` the generator already consumes into a `schemaVersion: 1` JSON document; `cli.py --out-dir` writes `domain-manifest.json` into the `generated_project` volume; compose service `generate-manifest` runs it as gate step 4. Offline pytest proves the builder, the CLI and the fixture cross-check; the manual gate proves the compose/script wiring pytest cannot reach (DD101/DD120).

## Architecture Decisions

| # | Decision | Alternatives rejected | Rationale |
|---|---|---|---|
| **DD121** | New app `apps.domain_manifest`: `builder/` (4 small modules) + `serialize.py` + `cli.py` + `apps.py`; `INSTALLED_APPS` right after `apps.postman_export`. | Folding it into `postman_export` (mixes OpenAPI conversion with model derivation, and its guard forbids `apps.spring_generator` outright); emitting it as a `GeneratedFile` in `generate_project_sources`. | One app per domain (DD109). The `spring-boot-generation` spec (L600/L609) forbids adding a Manifest to the aggregate, and the 41-file oracle is pinned in 3 test modules. |
| **DD122** | Source of truth is the `RelationalModel` (`build_sample_relational_model()`), not `docs/openapi.json` and not the generated tree. | B: parse the captured OpenAPI (loses relationships, inheritance, enum labels, and needs the smoke to have run); D: both (double the code, double the gate). | The relational model carries exactly the facts §28 asks for. Endpoints become *computed* rather than observed — the single residual risk, guarded by DD129. |
| **DD123** | `builder/` imports `apps.spring_generator.emit.naming` **directly** (`pascal_case`, `camel_case`, `relationship_base_name`, `resource_path_segment`, `screaming_snake_case`). The decoupling guard allowlists exactly that module path and rejects every other `apps.spring_generator.*` name. The `@OneToOne` rule (FK column set equals one of the table's `unique_constraints`) is **re-stated locally in 3 lines**, not imported. | Copying the naming functions (re-creates the drift this design exists to prevent); moving `naming.py` to a shared package (touches the proven generator app and its oracle); importing the private `context._is_one_to_one` (a private symbol, and `emit/context.py` drags `javatypes` + the whole context module in, making the allowlist meaningless). | `emit/naming.py` is pure (`re` + `emit.errors`) and `emit/__init__.py` is empty — verified — so the import loads no Jinja2 and no Django. A single naming source is what makes resource paths, field names and class names undriftable. |
| **DD124** | `serialize.py` is **duplicated** (~15 lines) from `postman_export/converter/serialize.py` instead of imported. The guarded set is `builder/**` + `serialize.py`; **`cli.py` is glue** and may import `apps.generation_runner.samples.sample_model`. | Importing the neighbour's serializer, or a new shared `apps.common` package. | Confirms DD109: both apps stay independently revertible, and nothing may import `apps.postman_export` (its own guard asserts that). The guarded-set divergence from DD109 is deliberate: `postman_export`'s CLI takes a *file*, ours must build the model in-process, exactly like `generation_runner/cli.py`. |
| **DD125** | Schema v1 (below): fixed key set per object, `null` instead of an omitted key; neutral type names from a closed `ColumnType` map; entities sorted by `name`, enums by `name`, relationships by `field`, subtypes by `name`, unique constraints by `name`; **attributes stay in table-column order** (the order the generated Entity/DTO uses); operations in the controller's own declaration order. | Omitting absent keys (consumers would branch on presence); sorting attributes alphabetically (loses the generated field order, which is real information). | A fixed key set plus `sort_keys` makes the text a pure function of the model. Only column order carries meaning that sorting would destroy. |
| **DD126** | `resourcePath` is `null` **iff** `operations` is `[]` — true exactly for tables with inheritance metadata (`discriminator_column is not None or discriminator_values`), which the renderer emits as entities + repository only, with no controller, DTO or service. | Emitting `/api/vehicles` for the hierarchy root anyway. | The generated app serves no such path (the committed `api-docs.json` has 5 resources and no `vehicles`), so emitting it would be a lie and would break DD129. |
| **DD127** | Determinism: `json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"`, written through `open(path, "w", encoding="utf-8", newline="\n")`. No ids, no timestamps, no `set` iteration reaching the output. Fixed output filename `domain-manifest.json` in `--out-dir`. | `write_text` (CRLF on a Windows host); a slugified filename (the gate needs a literal path). | Same recipe as DD112; byte-identity across two runs is a success criterion. |
| **DD128** | Compose service `generate-manifest` copies the `generate-postman` stanza: profile `jvm-verify`, `entrypoint: []`, `user: root`, `./backend:/app:ro` + `generated_project:/generated`, **no `depends_on`, no `rm -rf`**, literal command array. Gate step 4 appended after `generate-postman`. | `depends_on: generate-project` (would re-run the generator and wipe the volume, DD113); `sh -c` (DD83/DD84). | The script sequences steps explicitly (DD94); under `set -euo pipefail` a non-zero CLI exit stops the gate at step 4 and the `EXIT` trap still removes `gen-db`. The script defines **no new exit code** — it forwards the CLI's 1 or 2. |
| **DD129** | Drift guard: pytest asserts `{e["resourcePath"] for e in entities if e["resourcePath"]}` equals the distinct `/api/...` bases of `backend/apps/postman_export/tests/fixtures/api-docs.json`, and that every `operations[].path` appears in that document's `paths`. The fixture is read **read-only**, never regenerated here. | Trusting the computed paths; regenerating the fixture from this change. | It is a really-captured springdoc document; it is the only offline proof that computed endpoints match served endpoints. |
| **DD130** | pytest proves builder + CLI only. The compose stanza and gate step 4 are proven by `docs/ai/gate-evidence.md`: gate exit 0 with `docs/domain-manifest.json` present, plus **one negative check** — temporarily point the stanza's `--out-dir` at a path under the existing regular file `docs/openapi.json`, run the gate, record CLI exit 1 (`error:` on stderr, no traceback) and the non-zero gate exit, then revert and confirm `sha1(docker-compose.yml)` equals the pre-edit value. | Claiming a "contract test pins the compose command". | DD101: the backend container mounts only `backend/` as `/app`, so `scripts/` and `docker-compose.yml` are unreachable from tests. |
| **DD131** | Emit only declared or generated facts. No `searchable`, `sortable`, `defaultSort`, `auditable`, `readOnly`, `aliases`, no `generation_metadata`. Record the §33 UML-vs-own-profile split note and the follow-up (the mapper must carry `generation_metadata` before those fields can exist). | Emitting the fields with defaults so the manifest "looks" §33-complete. | A default is indistinguishable from a declaration to a consumer; §29's executor may only operate declared capabilities. |

**Verified by reading**: `Table/Column/ForeignKey/UniqueConstraint/EnumType` fields (`relational_mapping/domain/schema.py`); enum attributes carry `ColumnType.ENUM` + `enum_type_name` (`mapper.py` L217-228); `discriminator_column` is the literal `"class_type"` and `discriminator_values[class_id]` is the **UML class name** (`mapper.py` L271-275); inheritance tables render entities + repository only (`renderer.py` L63-108, L102-115); the controller's six mappings and statuses (`Controller.java.j2`); `resource_path = "/api/" + resource_path_segment(table.name)` (`context.py` L612); `_is_one_to_one` is private (`context.py` L147); the fixture's five resources and absence of `vehicles`; `emit/__init__.py` is empty; `INSTALLED_APPS` lists `apps.postman_export` after `apps.generation_runner`; the gate's `set -euo pipefail` + `EXIT` trap; last logged decision is DD120.
**Unverified (settled at apply against the real sample output)**: the exact entity count and the `unique_constraints` the mapper emits for the N:M join table `product_tag` (`_build_join_table` not read), hence whether any sample relationship is `oneToOne`; and the nullability of subclass-owned columns in the `vehicle` table.

## Data Flow

    sample_model ──map_to_relational──▶ RelationalModel
                                            │
        builder/ (+ emit.naming, DD123) ────┤
                                            ▼
    cli.py --out-dir ──serialize.write_json──▶ /generated/project/docs/domain-manifest.json
                                                        ▲
    gate step 4: docker compose run --rm generate-manifest

## Interfaces / Contracts

Schema v1 (one entity and one enum shown; every key is always present):

```json
{
  "schemaVersion": 1,
  "entities": [
    {
      "name": "Purchase",
      "table": "purchase",
      "resourcePath": "/api/purchases",
      "discriminatorColumn": null,
      "subtypes": [],
      "operations": [
        {"name": "create",   "method": "POST",   "path": "/api/purchases",      "successStatus": 201},
        {"name": "findById", "method": "GET",    "path": "/api/purchases/{id}", "successStatus": 200},
        {"name": "update",   "method": "PUT",    "path": "/api/purchases/{id}", "successStatus": 200},
        {"name": "delete",   "method": "DELETE", "path": "/api/purchases/{id}", "successStatus": 204},
        {"name": "list",     "method": "GET",    "path": "/api/purchases",      "successStatus": 200},
        {"name": "count",    "method": "GET",    "path": "/api/purchases/count","successStatus": 200}
      ],
      "attributes": [
        {"name": "id", "column": "id", "type": "uuid", "required": true, "primaryKey": true,
         "maxLength": null, "enum": null, "subtype": null},
        {"name": "status", "column": "status", "type": "enum", "required": true, "primaryKey": false,
         "maxLength": null, "enum": "PurchaseStatus", "subtype": null},
        {"name": "customerId", "column": "customer_id", "type": "uuid", "required": true,
         "primaryKey": false, "maxLength": null, "enum": null, "subtype": null}
      ],
      "relationships": [
        {"field": "customer", "attribute": "customerId", "column": "customer_id",
         "kind": "manyToOne", "target": "Customer", "required": true}
      ],
      "uniqueConstraints": []
    }
  ],
  "enums": [
    {"name": "PurchaseStatus",
     "values": [{"value": "PENDING", "label": "PENDING"}, {"value": "PAID", "label": "PAID"}]}
  ]
}
```

Derivation, field by field:

| Field | Derived from |
|---|---|
| `entities[].name` / `.table` | `pascal_case(table.name)` / `table.name` |
| `.resourcePath` | `"/api/" + resource_path_segment(table.name)`, or `null` (DD126) |
| `.discriminatorColumn` | `table.discriminator_column` |
| `.subtypes[]` | `{"name": pascal_case(v), "discriminatorValue": v}` for `discriminator_values[id]`, `id` in `source_class_ids[1:]`; sorted by name; `[]` otherwise |
| `.operations[]` | the fixed 6-row table above, `path` prefixed with `resourcePath`; `[]` when the table has inheritance metadata |
| `.attributes[]` | one per column **except** `table.discriminator_column` (the renderer skips it too): `name = camel_case(column.name)` (a FK column keeps its `Id` suffix, DD38), `column = column.name`, `type` from the map below, `required = not column.nullable`, `primaryKey = column.name == primary_key.column_names[0]`, `maxLength = column.length` (VARCHAR only, else `null`), `enum = pascal_case(column.enum_type_name)` or `null`, `subtype = discriminator_values.get(column.owning_class_id)` mapped through `pascal_case` when it is not the root class, else `null` |
| `.relationships[]` | one per FK column: `field = camel_case(relationship_base_name(column.name))`, `attribute` = the matching attribute name, `kind = "oneToOne"` when `frozenset(fk.column_names)` equals one of `table.unique_constraints[*].column_names` else `"manyToOne"`, `target = pascal_case(fk.referenced_table)`, `required = not column.nullable` |
| `.uniqueConstraints[]` | `{"name": uc.name, "columns": list(uc.column_names)}` |
| `enums[]` | `{"name": pascal_case(e.name), "values": [{"value": screaming_snake_case(l), "label": l}]}` — `value` is the wire value (`@Enumerated(EnumType.STRING)` serializes the Java constant), `label` the preserved UML label (DD32) |

Type map (closed over `ColumnType`, unknown member → `ValueError` → CLI exit 1): `UUID→uuid`, `VARCHAR→string`, `TEXT→text`, `INTEGER→integer`, `BIGINT→long`, `NUMERIC→decimal`, `BOOLEAN→boolean`, `DATE→date`, `TIMESTAMPTZ→datetime`, `ENUM→enum`.

```yaml
# docker-compose.yml — literal command array, no depends_on, no rm -rf (DD128)
generate-manifest:
  build: { context: ./backend, target: dev }
  profiles: [jvm-verify]
  entrypoint: []
  user: root
  volumes:
    - ./backend:/app:ro
    - generated_project:/generated
  command: ["python", "-m", "apps.domain_manifest.cli", "--out-dir", "/generated/project/docs"]
```

```bash
# scripts/verify-generated-project.sh — fourth sequential step
docker compose --profile jvm-verify run --rm generate-manifest
```

## File Changes

| File | Action | Size est. |
|---|---|---|
| `backend/apps/domain_manifest/__init__.py`, `apps.py` | Create | ~15 |
| `builder/__init__.py` (public API `build_manifest(model) -> dict`) | Create | ~12 |
| `builder/attributes.py` (type map, column → attribute) | Create | ~55 |
| `builder/relationships.py` (FK index, kind rule, relationship dicts) | Create | ~45 |
| `builder/entities.py` (operations table, subtypes, entity assembly) | Create | ~80 |
| `builder/manifest.py` (top level, enums, ordering) | Create | ~35 |
| `serialize.py` (duplicated, DD124) | Create | ~20 |
| `cli.py` (`--out-dir`, exit 0/1/2, no `django.setup()`) | Create | ~50 |
| `tests/` (5 modules, below) | Create | ~360 |
| `backend/config/settings.py` | Modify | +1 |
| `docker-compose.yml` | Modify (stanza + comment) | ~18 |
| `scripts/verify-generated-project.sh` | Modify (step 4 + comment) | ~5 |
| `openspec/specs/...` deltas, `docs/ai/` (gate-evidence, CURRENT_STATE, HANDOFF_LATEST, NEXT_STEPS, DECISIONS_LOG DD121-DD131, §33 split note) | Modify | ~60 |

**Authored total ≈ 755 lines** — inside the 800-line budget only if the tests stay table-driven (see below). No fixture is added.

## Testing Strategy

Strict TDD: each RED test precedes its module. Tests are **parametrized over the sample model** — one `pytest.mark.parametrize` table per behaviour, never one test function per entity.

| Layer | What | Module (est.) |
|---|---|---|
| Unit | attribute mapping: every `ColumnType` → neutral name, `required`, `maxLength` only on VARCHAR, `enum`, `primaryKey`, discriminator column excluded — one parametrized table | `tests/test_attributes.py` (~90) |
| Unit | relationship `kind`/`target`/`field`/`attribute`, FK attribute keeps its `Id` suffix; `oneToOne` proven with a hand-built table whose unique constraint matches the FK | `tests/test_relationships.py` (~70) |
| Integration (offline) | full sample manifest: entity set, `resourcePath`/`operations` pairing (DD126), `vehicle` subtypes `Car`/`Truck`, enum values, top-level ordering | `tests/test_manifest.py` (~90) |
| Determinism | two `build_manifest` calls produce equal dicts; serialized text is byte-identical, ends with exactly one `\n`, contains no `\r` | `tests/test_determinism.py` (~30) |
| Drift guard | DD129 fixture cross-check, both directions | inside `tests/test_manifest.py` (~25) |
| CLI | exit 0 writes `domain-manifest.json`; exit 1 on an unwritable out-dir (message, no traceback, nothing written); exit 2 names `--out-dir`; `django.setup` trap + its control; two runs byte-identical | `tests/test_cli.py` (~80) |
| Decoupling guard | AST scan of `builder/**` + `serialize.py`: forbids `django`, `apps.generation_runner`, `apps.postman_export`, `apps.uml_*`, and every `apps.spring_generator.*` name except the exact allowlist `apps.spring_generator.emit.naming`; a triangulation case proves the allowlist rejects `apps.spring_generator.emit.context`; subprocess import leaves `django`/`jinja2`/`apps.generation_runner` out of `sys.modules`; no other app imports `apps.domain_manifest`; `INSTALLED_APPS` position; no host/port/URL literal in app source | `tests/test_builder_decoupling.py` (~90) |
| Manual gate | step 4 writes `docs/domain-manifest.json`; one negative check (DD130) | `bash scripts/verify-generated-project.sh` + `docs/ai/gate-evidence.md` |

**Failure modes / exit codes**

| Where | Condition | Code |
|---|---|---|
| CLI | unwritable/blocked out-dir, any `OSError` | `1` (stderr `error: ...`, no traceback) |
| CLI | builder rejection (`InvalidJavaIdentifierError`, `InvalidResourcePathError`, `ValueError` from the closed type map) | `1` |
| CLI | usage error (missing `--out-dir`) | `2` (argparse) |
| gate | step 4 non-zero | `set -e` stops; `EXIT` trap still removes `gen-db`; the CLI code is the gate's code |

## Threat Matrix

Shell/compose boundary is touched, so the matrix is recorded.

| Boundary | Applicability | Response |
|---|---|---|
| Documentation-like paths | N/A — no file is classified or executed by content; the manifest is written as data. |
| Git repository selection / commit state / push state / PR commands | N/A — no `git`, index, push or PR automation. |
| **Shell/compose argument composition** | Applicable | Literal `command` array only (no `sh -c`, no `eval`, no `rm -rf`); the only container paths live in `docker-compose.yml`; `MSYS_NO_PATHCONV=1` is already exported by the gate script. Proven by the gate, not pytest (DD130). |
| **Read-only fixture** | Applicable | `api-docs.json` is opened read-only by the drift guard and is never rewritten by this change. |

## Work Units / Rollout

Two sequential, independently revertible slices inside one PR (`delivery_strategy: single-pr`).

1. **Slice 1** — `builder/` + `serialize.py` + `cli.py` + `apps.py` + `INSTALLED_APPS` + the 5 pytest modules. Finishes green with `pytest -q`, Docker-free and offline. ~575 lines.
2. **Slice 2** — compose stanza, gate step 4, gate run + negative check recorded in `gate-evidence.md`, spec deltas, `docs/ai/` updates incl. DD121-DD131 and the §33 split note. ~180 lines. Must not start before slice 1 is green.

No migration: no models, no Django schema impact; the app is inert until its CLI is invoked.

## Rollback

Revert slice 2 → the gate returns to its three proven steps, byte-unchanged. Revert slice 1 → `apps.domain_manifest` and its `INSTALLED_APPS` line disappear; nothing imports it (the guard asserts this). `postman_export` is read-only throughout; the generated project is untouched either way, and the manifest lives only in the named volume, wiped by the next `generate-project`.

## Open Questions

- [ ] Apply-time (non-blocking): the sample's `product_tag` join table is a full CRUD entity today; whether either of its FKs lands as `oneToOne` depends on the unique constraints `_build_join_table` emits — assert against the real built manifest, not against an assumption.
- [ ] Apply-time: nullability of subclass-owned columns in `vehicle` decides `required` for `subtype`-tagged attributes.
