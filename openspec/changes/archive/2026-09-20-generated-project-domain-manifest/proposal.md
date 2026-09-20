# Proposal: Generated Project Domain Manifest

## Intent

§28 and §37 item 16. The spec requires a `Domain Manifest` derived from the model: the declarative map (entities, attributes, types, relationships, allowed operations, validations) consumed by §29's in-app assistant and §26/§27's frontend CRUD inference. Nothing emits it today, so every consumer would re-derive the domain by parsing Java or guessing from OpenAPI.

## Scope

### In Scope

- New app `apps.domain_manifest`, sibling of `postman_export`: pure `builder/` + serialize + plain `__main__` CLI (`--out-dir`), `apps.py`, no models/migrations, INSTALLED_APPS after `postman_export`, decoupling guard allowing only the one-way import of `spring_generator.emit.naming`.
- Output `docs/domain-manifest.json` (fixed name) in volume `generated_project`; deterministic dump (indent=2, sort_keys, ensure_ascii=False, trailing newline, `newline="\n"`); `schemaVersion: 1`.
- Content: `entities[]` (name, table, resourcePath, `operations[]` — the 6 CRUD ops, empty for inheritance roots — `attributes[]` {name, column, type, required, maxLength, enum, primaryKey}, `relationships[]`, subtypes, uniqueConstraints) and `enums[]`. Only what is declared or generated today.
- Compose service `generate-manifest` (profile `jvm-verify`, no `depends_on`, no `rm -rf`, literal command array) as gate step 4 after `generate-postman`, its non-zero CLI exit propagated by the gate.
- Drift guard: pytest asserts manifest resource paths equal the paths in the committed `postman_export` fixture `api-docs.json` (read-only).
- Docs: the UML vs own-profile split note §33 requires, plus the deferred-metadata follow-up.

### Out of Scope

- §33 `generation_metadata`, aliases, searchable/sortable/defaultSort/auditable/readOnly — the relational mapper does not carry them; fabricating them would lie in the contract.
- Filtering/search API, frontend/mobile generation, assistant/AssistantCommand, auth.
- Embedding the manifest in the 41-file Spring tree (`spring-boot-generation` forbids it), deriving it from OpenAPI, real-project CLI input (sample model only).

## Capabilities

### New Capabilities

- `domain-manifest-export`: manifest schema v1, derivation from the RelationalModel, determinism rules, CLI contract.

### Modified Capabilities

- `generated-project-verification`: `Compose Chain Contract` (`generate-manifest` shape), `Single Gate Command` (fourth step), `Manual Gate Evidence` (manifest result), `Boot Change Isolation` wording.

## Approach

Derive from the `RelationalModel` — the model the generator already consumes — not from OpenAPI, not from the generated tree. Reusing `spring_generator.emit.naming` makes resource paths, column names and class names undriftable by construction, and the builder knows inheritance roots have no controller, which an OpenAPI-derived manifest could only guess. springdoc stays the sole OpenAPI producer: a manifest is not the API contract, so the earlier rejection of deriving OpenAPI from the relational model does not apply. The residual risk — computed rather than observed endpoints — is guarded by the fixture cross-check and the live gate step. Serialize is duplicated rather than imported from `postman_export` so both apps stay independently revertible (DD109); design may overturn this with a better reason.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/apps/domain_manifest/` | New | Builder, serialize, CLI, decoupling guard, tests |
| `backend/config/settings*` | Modified | INSTALLED_APPS after `postman_export` |
| `docker-compose.yml` | Modified | `generate-manifest` service |
| `scripts/verify-generated-project.sh` | Modified | Fourth sequential step |
| `openspec/specs/generated-project-verification/` | Modified | Delta spec |
| `docs/ai/` | Modified | Gate evidence, CURRENT_STATE, DECISIONS_LOG (DD101/DD105) |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Endpoint drift (paths computed, not read from springdoc) | Medium | Fixture cross-check plus live gate step |
| No spec-defined JSON shape; consumers arrive later | Medium | `schemaVersion: 1`, additive-only evolution |
| Inheritance APIs added later leave the builder stale | Low | Single naming source, ops from the emitter's own rule |
| Manifest reads as §33-complete while metadata is absent | Medium | Emit declared facts only; gap recorded as follow-up |
| Review budget overshoot (last change hit ~1246 lines) | Medium | Two-slice split inside one PR (below) |

## Rollback Plan

Two independent reverts. Revert slice 2 (compose service, gate step 4, evidence, docs) and the gate returns to its three proven steps. Revert slice 1 and `apps.domain_manifest` disappears with its INSTALLED_APPS entry; nothing imports it (guard enforced). `postman_export` is used read-only; the generated project is untouched either way.

## Dependencies

- Docker plus network for the manual gate (step 4 evidence and the negative check).
- Committed fixture `backend/apps/postman_export/tests/fixtures/api-docs.json`, read-only.

## Size Forecast

~250 production lines, 350-450 test lines, ~25 compose/script, ~60 docs = **700-850 changed lines**, no large fixture. That sits at or just over the 800-line budget, so plan **two sequential slices inside the single PR**: slice 1 = builder + serialize + CLI + pytest (fixture cross-check, decoupling guard); slice 2 = compose service + gate step 4 + spec delta + evidence + docs. `sdd-tasks` must order work units so slice 1 is independently green before slice 2 starts.

## Success Criteria

- [ ] Gate recorded at exit 0 with step 4 producing `docs/domain-manifest.json`, plus one negative check.
- [ ] Every generated CRUD resource listed with its real resource path; inheritance roots have empty `operations[]`.
- [ ] Two runs on the same model produce byte-identical output.
- [ ] Manifest resource paths equal the committed `api-docs.json` paths for the sample model.
- [ ] `pytest -q` stays green, Docker-free and offline; no app imports `domain_manifest`.
- [ ] No absent §33 field fabricated; UML vs own-profile split note recorded.
