# Design: Generated Project OpenAPI via springdoc

§37 item 14, part 1. Inputs: `proposal.md`, `exploration.md`. Decisions continue the project sequence from **DD103** (last used: DD102, `generated-project-boot-smoke`).

## Technical Approach

One dependency threaded through the existing single-sourcing chain — `emit/versions.py` → `BuildScriptContext` → `renderer.generate_project_scaffold_sources` → `build.gradle.j2` — plus one assertion block in `scripts/boot-smoke.sh`. No generated Java, no `application.yml` change: springdoc infers the document from the already-emitted MVC controllers and jakarta-validated DTOs. The generated project carries a `@RestControllerAdvice`, the historical breaker of `/v3/api-docs`, so the smoke assertion is the regression proof.

**Chain correction (not in the proposal's affected areas):** `renderer.py:257-262` passes every context field to the template by name, so it MUST gain `springdoc_version=build_script_context.springdoc_version` or Jinja raises `UndefinedError` due to `StrictUndefined`.

## Architecture Decisions

| # | Decision | Alternatives rejected | Rationale |
|---|---|---|---|
| DD103 | `SPRINGDOC_VERSION: Final[str] = "3.1.1"` in `versions.py` (after `SPRING_BOOT_VERSION`, docstring naming the Boot-4.1.0 build gap); `springdoc_version: str` as the **last** field of `BuildScriptContext`; set in `build_build_script_context` in declaration order; forwarded by `renderer.py`. | A literal in the template; relying on the Boot BOM; a separate `SpringdocContext`. | The Boot BOM does not manage springdoc, so a version is mandatory somewhere; DD62 says that somewhere is `versions.py`, and DD72 enforces it by scan. Appending the field keeps every existing positional construction in `test_scaffold_context.py` valid and the frozen-dataclass equality readable. |
| DD104 | Template line `    implementation 'org.springdoc:springdoc-openapi-starter-webmvc-api:{{ springdoc_version }}'`, placed **after** the three `spring-boot-starter-*` lines and **before** `runtimeOnly 'org.postgresql:postgresql'`. | The `-ui` starter; first in the block; `runtimeOnly`. | Four-space indent + single quotes matches every neighbour. The block reads BOM → Boot starters → third-party compile deps → runtime driver; springdoc is the only non-Boot `implementation`, so it belongs between them. `-ui` ships Swagger UI web assets nobody consumes in this slice. `runtimeOnly` would hide the annotations springdoc needs at compile time in later slices. |
| DD105 | The smoke asserts OpenAPI **after** the CRUD round-trip, immediately before `PASS`: `assert_status 200 GET /v3/api-docs`, then two pure-bash `case` matches on the whitespace-stripped `$BODY` for `"openapi":` and `"/api/customers"`. Body mismatch gets a **new typed exit code 7**; the 200 mismatch reuses `assert_status`'s 6. | Asserting right after readiness; reusing exit 6; `jq`; `grep`. | Placing it last means a springdoc regression is reported with CRUD already green — exactly the diagnostic split the `@RestControllerAdvice` risk row needs, instead of masking the pre-existing proof. A distinct code keeps the table's "one code, one stage" property: 6 is *transport/status*, 7 is *document content*. `jq` is absent from the Gradle image (DD100). Whitespace stripping is safe because both needles are quoted JSON tokens. The header comment's exit-code table and `test_boot_smoke_contract.py`'s docstring both gain the new row. |
| DD106 | pytest pins the **generated side only**: `test_project_scaffold_sources.py` oracle gains the line and `_expected_build_gradle` gains `springdoc_version=SPRINGDOC_VERSION`; `"springdoc"` is removed from the `excluded` parametrization and inverted into a positive `test_build_gradle_declares_the_springdoc_starter_at_the_pinned_version`; the DD72 scan gains `r"\b3\.1\.1\b"` with id `springdoc-version`; `test_boot_smoke_contract.py` adds one test asserting the coordinate is present in `generate_project_sources(...)["build.gradle"]`. | Reading `scripts/boot-smoke.sh` from pytest to pin the `/v3/api-docs` literal. | DD101 stands: the test process runs with `/app` = `backend/`, so `scripts/` is **unreachable** — a script-literal pin is impossible, not merely undesirable. What pytest *can* prove is that the dependency making `/v3/api-docs` exist is declared, and `/api/customers` (the body needle) is already pinned by `test_controller_is_mounted_on_api_customers`. The `\b` guards make `\b3\.1\.1\b` reject `4.1.1`, `9.7.1`, `13.1.1` and `3.1.10`; the literal lives only in `versions.py`, so the scan stays green by construction. |
| DD107 | The gate is recorded in `gate-evidence.md`: positive run, plus a negative check that temporarily replaces `"/api/customers"` with a bogus fragment, observes exit 7, and is reverted before commit. The Boot 4.1.0-vs-4.1.1 gap is recorded as an observed fact ("springdoc 3.1.1 is built on Boot 4.1.0; booted green on 4.1.1 on <date>"). | Trusting the FAQ's compatibility claim; skipping the negative case; a permanent failure toggle. | A gate never observed red is not evidence (DD102 precedent). Editing one needle exercises the new code path without a service, a flag, or a DB change. The version gap is resolvable only by observation, so the evidence file, not the design, is where the claim belongs. |

**Fix-forward rule.** If the gate shows `/v3/api-docs` failing because of `GlobalExceptionHandler`, fix forward **only** if the fix is a template-local annotation or ordering change. Anything needing a Java `@Configuration` class (forbidden: "no `config/`") or an `application.yml` key stops the slice and is reported as a finding.

## Data Flow

    versions.py SPRINGDOC_VERSION
       └→ build_build_script_context → BuildScriptContext.springdoc_version
            └→ renderer.generate_project_scaffold_sources(springdoc_version=…)
                 └→ build.gradle.j2 → build.gradle → Gradle → springdoc on the classpath
                      └→ boot: MVC controllers + jakarta DTOs → GET /v3/api-docs (JSON)
                           └→ boot-smoke.sh: 200 + body ⊇ {"openapi":, "/api/customers"}

## File Changes

| File | Action | ~Lines | Description |
|---|---|---|---|
| `backend/apps/spring_generator/emit/versions.py` | Modify | +4 | DD103 constant + docstring |
| `backend/apps/spring_generator/emit/scaffold_context.py` | Modify | +3 | DD103 field, import, builder arg |
| `backend/apps/spring_generator/emit/renderer.py` | Modify | +1 | DD103 render kwarg (chain correction) |
| `backend/apps/spring_generator/emit/templates/build.gradle.j2` | Modify | +1 | DD104 coordinate |
| `scripts/boot-smoke.sh` | Modify | +14 | DD105 assertion + exit-code comment |
| `backend/apps/spring_generator/tests/test_scaffold_context.py` | Modify | +5 | DD103 constant value, equality, propagation |
| `backend/apps/spring_generator/tests/test_project_scaffold_sources.py` | Modify | +12 | DD106 oracle, inverted param, DD72 scan |
| `backend/apps/generation_runner/tests/test_boot_smoke_contract.py` | Modify | +10 | DD106 coordinate pin, docstring |
| `openspec/.../specs/{spring-boot-generation,generated-project-verification}/spec.md` | Create | 60 | Deltas per proposal |
| `openspec/changes/.../gate-evidence.md` | Create | 40 | DD107 |
| `docs/ai/{CURRENT_STATE,HANDOFF_LATEST,NEXT_STEPS,DECISIONS_LOG}.md` + session note | Modify | 50 | DD103–DD107 |

## Interfaces / Contracts

```python
SPRINGDOC_VERSION: Final[str] = "3.1.1"          # versions.py

@dataclass(frozen=True)
class BuildScriptContext:
    group: str; version: str; spring_boot_version: str
    java_version: int; springdoc_version: str      # NEW, last
```

```bash
# 9. OpenAPI document (springdoc). Pure bash, no jq (DD100/DD105).
assert_status 200 GET /v3/api-docs
DOC=$(<"$BODY"); DOC=${DOC//[[:space:]]/}
case $DOC in *'"openapi":'*) ;; *) die 7 "/v3/api-docs carries no openapi field" ;; esac
case $DOC in *'"/api/customers"'*) ;; *) die 7 "/v3/api-docs does not document /api/customers" ;; esac
```

## Testing Strategy

| Layer | What | How |
|---|---|---|
| Unit (pytest, offline, Docker-free) | DD103 constant/field/propagation; DD106 oracle equality, positive springdoc assertion, DD72 scan, coordinate pin | **RED first** for this whole half: write all test edits, watch them fail, then touch `versions.py`/`scaffold_context.py`/`renderer.py`/the template. TDD order: `test_scaffold_context` → `test_project_scaffold_sources` → `test_boot_smoke_contract`. |
| Gate (manual, DD107) | 200 + document content on a real boot | `bash scripts/verify-generated-project.sh` → exit 0 with `GET /v3/api-docs -> 200`. The bash half is untestable from pytest (DD101/DD106), so this run is its only proof. |
| Gate negative (manual, DD107) | The new assertion can fail | Temporarily change the `"/api/customers"` needle to a bogus fragment → expect exit 7 → revert. |

## Threat Matrix

| Boundary | Applicability | Design response | Planned RED test |
|---|---|---|---|
| Shell argument composition | **Applicable** — a new HTTP path reaches curl | `/v3/api-docs` is a **constant literal** passed through `assert_status`'s argument array (DD99); no interpolation, no `eval`, no `sh -c` | Gate evidence: the `GET /v3/api-docs -> 200` log line |
| Response data reaching a command | **Applicable** — a new response body is parsed | The body is matched by bash `case` only; **no value from it reaches a URL, a variable used in a command, or a file path** — unlike DD100's id | Gate negative: bogus needle → exit 7 |
| Secrets in process arguments / logs | **Applicable** — `assert_status` dumps the body on mismatch | The dump is already capped at `tail -c 2000`; the OpenAPI document carries schema metadata, not credentials (no `application.yml` change, DD103) | Gate evidence: failure dump inspected once |
| Destructive shell | **N/A** — no new cleanup, removal, or file write | — | — |
| Git/PR automation, executable-file classification, routing | **N/A** — none introduced | — | — |

## Migration / Rollout

No migration. Additive: one dependency in generated output, one smoke block. `pytest -q` stays offline and Docker-free. Rollback per the proposal — revert the commit; the scaffold loses springdoc and the gate returns to compile + CRUD.

## Open Questions

- [ ] None blocking. The Boot 4.1.0/4.1.1 gap and the `@RestControllerAdvice` interaction are resolved by the DD107 gate run, with DD107's fix-forward rule as the stop condition.
