# Proposal: Generated Project OpenAPI via springdoc

## Intent

The generated Spring backend compiles, boots and serves CRUD, but describes itself nowhere. §37 item 14 needs a machine-readable OpenAPI document as the source for the Postman collection and the Domain Manifest. The stack decision is already made (`DECISIONS_LOG.md` 2026-09-19: §22 wins — springdoc owns the **generated** backend's document). This slice makes the generated project serve it, and proves it on a real boot.

## Scope

### In Scope

- `org.springdoc:springdoc-openapi-starter-webmvc-api` **3.1.1** only (no Swagger UI) in `build.gradle.j2`.
- Version single-sourced as `SPRINGDOC_VERSION` in `emit/versions.py` → `BuildScriptContext.springdoc_version` (the Boot BOM does not manage springdoc).
- Boot smoke: after readiness, `GET /v3/api-docs` returns 200 and the body contains `openapi` and `/api/customers` (pure bash, no `jq`).
- Tests: scaffold oracle, DD72 literal scan (`3.1.1`), inverted "springdoc excluded" assertion, `/v3/api-docs` pinned in `test_boot_smoke_contract.py`.
- Recorded manual gate run, positive and negative.

### Out of Scope

- Swagger UI, `application.yml` change, controller/DTO annotations, Java `@Configuration`.
- Static `openapi.json` export → Postman change (options: the smoke writes the body into the `generated_project` volume, or the springdoc Gradle plugin; deriving it from the relational model is rejected — it bypasses springdoc).
- operationId collisions, tags, `ProblemDetail` documentation → Postman/Domain-Manifest.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `spring-boot-generation`: "Project Scaffold Generation" — drop "MUST NOT declare springdoc/OpenAPI", require the pinned starter and its single-sourced version; update the scenario "build.gradle declares the verified starters and driver only".
- `generated-project-verification`: ADD "OpenAPI Document Served" **[manual]**; extend "Generated Contract Pin" **[pytest]**; narrow "Boot Change Isolation" (its "MUST NOT add a version literal to `versions.py`" and "MUST NOT change generated sources" are both contradicted now). Both Purpose lines need their OpenAPI wording checked.

## Approach

One dependency line threaded the existing way: constant → context field → template. springdoc infers the document from the already-generated MVC controllers and jakarta-validated DTOs, so no generated Java changes. The generated project has a `@RestControllerAdvice` — historically the one thing that breaks `/v3/api-docs` — so the smoke assertion is the regression proof, not a formality.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `emit/versions.py`, `emit/scaffold_context.py` | Modified | Constant + context field |
| `templates/.../build.gradle.j2` | Modified | Starter coordinate |
| `scripts/boot-smoke.sh` | Modified | `/v3/api-docs` assertion |
| `test_project_scaffold_sources.py`, `test_scaffold_context.py`, `test_boot_smoke_contract.py` | Modified | Oracles, scan, pins |
| `openspec/specs/{spring-boot-generation,generated-project-verification}` | Modified | Deltas |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| 3.1.1 is built on Boot 4.1.0, not 4.1.1 | Medium | The gate on 4.1.1 is the proof; record the gap honestly |
| `@RestControllerAdvice` breaks `/v3/api-docs` | Medium | Fix forward only if small, else stop and report the finding |
| New Maven download flakes the gate | Medium | Same class as existing deps; rerun and record |
| Stale "no OpenAPI" spec wording | Medium | Spec phase checks lines ~5, ~243, ~600, ~609 |

## Rollback Plan

Revert the commit: one constant, one field, one template line, one smoke block. The scaffold loses springdoc; the gate returns to compile + CRUD.

## Dependencies

- Docker and network for the manual gate (Maven Central resolution of the new coordinate).

## Success Criteria

- [ ] `build.gradle` declares the starter at a version literal present only in `versions.py`.
- [ ] Gate recorded: `/v3/api-docs` → 200, body contains `openapi` and `/api/customers`.
- [ ] Negative check recorded: a bogus path fragment fails the assertion, then reverted.
- [ ] `pytest -q` stays green, Docker-free and offline.
