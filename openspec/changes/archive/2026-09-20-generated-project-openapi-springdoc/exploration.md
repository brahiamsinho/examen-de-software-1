# Exploration: springdoc-openapi in the GENERATED Spring backend (§37 item 14, part 1)

> Faithful copy of Engram observation `#699` (`sdd/generated-project-openapi-springdoc/explore`),
> persisted to disk because the explore agent had no Write tool.

## Verified facts (evidence)

- Artifact: `org.springdoc:springdoc-openapi-starter-webmvc-api` (API only; the `-ui` variant adds Swagger UI). Latest stable 3.1.1 (Maven Central metadata `https://repo1.maven.org/maven2/org/springdoc/springdoc-openapi-starter-webmvc-api/maven-metadata.xml`; files dated 2026-09-06). 3.x series: 3.0.0..3.0.3, 3.1.0, 3.1.1. 2.8.x is Boot 3 only.
- 3.1.1 parent POM (`https://repo1.maven.org/maven2/org/springdoc/springdoc-openapi/3.1.1/springdoc-openapi-3.1.1.pom`) is built on Spring Boot 4.1.0, swagger-core 2.2.55; the starter depends on `spring-boot-webmvc` (Boot 4 modular). springdoc FAQ (`https://springdoc.org/faq.html`): 3.x is compatible with Spring Boot 4; recommends latest stable 3.1.1. Boot 4.1.1 is a patch of 4.1.0 -> compatible in principle; the real proof is the boot smoke. The Boot BOM does NOT manage springdoc -> an explicit version is required.
- Known Boot 4 caveats: none found for 3.1.x; Jackson 3 issues (#3175 Kotlin/`@Schema`, #3095 HAL) were 3.0.0-M/RC era. Historical risk class: `@RestControllerAdvice` breaking `/v3/api-docs` on version mismatch (#3045, #2762); the generated project HAS a `@RestControllerAdvice` (`GlobalExceptionHandler`, returns `ProblemDetail`) -> the smoke `GET /v3/api-docs` is exactly the right regression proof.
- Default endpoint `/v3/api-docs` (JSON), `/v3/api-docs.yaml`; Swagger UI only with `-ui` at `/swagger-ui.html`.

## Current state

- `versions.py` pins `SPRING_BOOT_VERSION`, `JAVA_VERSION`, `PROJECT_VERSION`, `GRADLE_VERSION`; `scaffold_context.BuildScriptContext` (frozen dataclass: `group`, `version`, `spring_boot_version`, `java_version`) feeds `build.gradle.j2`; the DD72 test scans `emit/**/*.py` (except `versions.py`) + templates for the literals `4.1.1`/`9.7.1`/`21`.
- `build.gradle.j2` deps: BOM platform, starters `webmvc`/`data-jpa`/`validation`, `runtimeOnly postgresql`. `application.yml.j2`: six env placeholders only.
- Controller: plain Spring MVC (`@RequestMapping`, `@Valid @RequestBody`, `@ResponseStatus`), DTOs with getters/setters and jakarta validation; springdoc infers everything.
- `boot-smoke.sh`: bash only (no `jq`), single curl call site `_http`/`assert_status`, runs in the `jvm-boot-smoke` compose service, project in the named volume `generated_project` (rw). Literals pinned by `generation_runner/tests/test_boot_smoke_contract.py`.

## Recommendation

Add ONLY `springdoc-openapi-starter-webmvc-api` 3.1.1 (smaller, no UI assets; the spec needs a machine-readable document for Postman/Manifest). Single-source: `SPRINGDOC_VERSION: Final[str] = "3.1.1"` in `versions.py`; add `springdoc_version` to `BuildScriptContext`; template line `implementation 'org.springdoc:springdoc-openapi-starter-webmvc-api:{{ springdoc_version }}'`. No `application.yml` change (defaults suffice; keeps the "MUST NOT emit OpenAPI" YAML rule and `test_project_config_sources` intact). Smoke: after readiness, `assert_status 200 GET /v3/api-docs` and a pure-bash `case` match that the body contains `"openapi"` and `"/api/customers"` (no `jq`). Runtime-only; NO static export in this slice (no consumer yet; Modelia has no running Spring app at generation time, so the Postman change must decide how to capture a static `openapi.json` — cheapest: the smoke/gate saves the body into the `generated_project` volume; `springdoc-openapi-gradle-plugin` also boots the app).

## Spec deltas

- `spring-boot-generation`: MODIFIED "Project Scaffold Generation" (remove "MUST NOT declare springdoc/OpenAPI", add the springdoc starter declaration + pinned-version single-sourcing; the scenario "declares the verified starters and driver only" loses "no springdoc"). The requirement at line ~243 (`application.yml` MUST NOT emit OpenAPI) stays valid untouched. Lines ~5/~600/~609 (no OpenAPI artifact in the model/aggregate output) remain true (a dependency is not an artifact) — clarify wording only if needed.
- `generated-project-verification`: ADDED "OpenAPI Document Served" (smoke, **[manual]**) + extend "Generated Contract Pin" **[pytest]**; NOTE "Boot Change Isolation" says MUST NOT change generated sources — a change-scoped requirement sitting in the main spec; it should be MODIFIED/narrowed to avoid a contradiction.
- Tests: `test_project_scaffold_sources.py` (the oracle `build.gradle` adds the springdoc line; remove `springdoc` from the excluded params; add the springdoc-version literal to the DD72 scan, e.g. `r"\b3\.1\.1\b"`), `test_scaffold_context.py` (new constant + field in `BuildScriptContext` equality), `test_boot_smoke_contract.py` (pin the `/v3/api-docs` literal in the script). The deployable-value scan (`http://`, `localhost`, `password`...) still passes with the coordinate added.

## Annotations

None required. Known later needs (§25/§28), out of scope: operationId collisions (springdoc defaults to the method name -> `create`, `create_1`... across controllers), default tags `customer-controller`, `ProblemDetail` error responses may not be documented without `@ResponseStatus`; fixing operationIds needs an `OperationCustomizer` (Java `@Configuration` -> conflicts with the "no `config/`" rule) or per-controller `@Operation(operationId)` emission — decide in the Postman/Manifest change.

## Risks / open decisions

- Only genuinely user-owned open point: none blocking. Optional: whether the Postman change wants a static export (deferred).
- Risks: springdoc 3.1.1 is built on Boot 4.1.0, not 4.1.1 (the smoke proves it); a new Maven download in the gate (network; same as the existing deps); a first gate run is needed as recorded evidence; `@RestControllerAdvice` interaction.
- Size: ~120-200 changed lines (`versions.py` 3, `scaffold_context` 3, template 1, 3 test files ~40, smoke script ~15, spec deltas ~60, gate evidence) << 800 budget.
- Note: `exploration.md` was NOT written to openspec (the explore agent had no Write/Bash tool); the orchestrator should write it from this observation if the hybrid file is required.
