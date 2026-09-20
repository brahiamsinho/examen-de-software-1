# Tasks: Generated Project OpenAPI via springdoc

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~150-200 (code+tests ~50, script ~14, evidence ~40, docs ~50) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | single-pr |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Springdoc dep single-sourced + smoke block + evidence + docs | PR 1 | `docker compose exec -T backend pytest -q apps/spring_generator apps/generation_runner` | `bash scripts/verify-generated-project.sh` (exit 0, `GET /v3/api-docs -> 200`) | Revert the commit |

## Phase 1: RED tests (Docker-free, DD103-DD107; write all, watch fail)

- [x] 1.1 `backend/apps/spring_generator/tests/test_scaffold_context.py`: assert `SPRINGDOC_VERSION == "3.1.1"`, `springdoc_version` last field, equality and propagation. (DD103; Project Scaffold Generation: pinned versions from one module)
- [x] 1.2 `backend/apps/spring_generator/tests/test_project_scaffold_sources.py`: add oracle line + `springdoc_version=SPRINGDOC_VERSION` in `_expected_build_gradle`. (DD104/DD106; scenario: starter at single-sourced version)
- [x] 1.3 Same file: remove `"springdoc"` from `excluded` and add `test_build_gradle_declares_the_springdoc_starter_at_the_pinned_version`; keep `-ui`/actuator excluded. (DD106; scenario: starters, springdoc and driver only)
- [x] 1.4 Same file: add DD72 scan `r"\b3\.1\.1\b"` id `springdoc-version` (versions.py only). (DD106; scenarios: literal in versions.py only / no literal outside versions.py)
- [x] 1.5 `backend/apps/generation_runner/tests/test_boot_smoke_contract.py`: assert the springdoc coordinate in `generate_project_sources(...)["build.gradle"]`; add exit 7 row to docstring. (DD105/DD106; Generated Contract Pin)
- [x] 1.6 Run `docker compose exec -T backend pytest -q apps/spring_generator apps/generation_runner`; confirm only the new tests fail.

## Phase 2: GREEN (order matters; renderer is the load-bearing step)

- [x] 2.1 `backend/apps/spring_generator/emit/versions.py`: add `SPRINGDOC_VERSION: Final[str] = "3.1.1"` after `SPRING_BOOT_VERSION`, docstring naming the Boot 4.1.0 build gap. (DD103)
- [x] 2.2 `backend/apps/spring_generator/emit/scaffold_context.py`: import it, add `springdoc_version: str` as last `BuildScriptContext` field, set in `build_build_script_context`. (DD103)
- [x] 2.3 `backend/apps/spring_generator/emit/renderer.py` (`generate_project_scaffold_sources`, ~L257-262): pass `springdoc_version=build_script_context.springdoc_version`; without it Jinja raises `UndefinedError` due to `StrictUndefined`. (DD103 chain correction)
- [x] 2.4 `backend/apps/spring_generator/emit/templates/build.gradle.j2`: add the 4-space-indented `springdoc-openapi-starter-webmvc-api:{{ springdoc_version }}` line after the three Boot starters, before `runtimeOnly` postgresql. (DD104)
- [x] 2.5 Re-run Phase 1 command; all green (Boot BOM, no `-ui`, no `\b3\.1\.1\b` outside versions.py).

## Phase 3: Smoke script

- [x] 3.1 `scripts/boot-smoke.sh`: after the CRUD round-trip, before `PASS`, add `assert_status 200 GET /v3/api-docs` + two pure-bash `case` needles (`"openapi":`, `"/api/customers"`) exiting 7 via `die`. (DD105; Requirement: OpenAPI Document Served)
- [x] 3.2 Same file: add code 7 (document content) to the header exit-code table; 6 stays transport/status. (DD105)

## Phase 4: Manual gate (DD107)

- [x] 4.1 Run `bash scripts/verify-generated-project.sh`; expect exit 0 with `GET /v3/api-docs -> 200`. (Scenario: Document served)
- [x] 4.2 Write `openspec/changes/generated-project-openapi-springdoc/gate-evidence.md`: date, generated `build.gradle` springdoc line, springdoc jar and boot log lines (built on Boot 4.1.0, booted on 4.1.1), threat-matrix log lines. (DD107)
- [x] 4.3 Negative check: change `"/api/customers"` needle to a bogus fragment, run the gate, observe exit 7 and the capped failure dump; record; revert. (Scenario: Negative check fails the gate)
- [x] 4.4 Confirm `docker compose config --services` is unchanged, no `down` was used, and the gen-db container/volume is removed afterwards; note in evidence. (Requirement: Boot Change Isolation)

## Phase 5: Full suite

- [x] 5.1 Run `docker compose exec -T backend pytest -q` (full backend); green and offline.

## Phase 6: Findings

- [x] 6.1 If the first boot shows a springdoc/`GlobalExceptionHandler` incompatibility, record it in `openspec/changes/generated-project-openapi-springdoc/gate-evidence.md`. Fix forward only if template-local (annotation/ordering); a Java `@Configuration` or `application.yml` key means STOP and report `blocked`. (Requirement: Fix-Forward Findings; DD107)

## Phase 7: Docs

- [x] 7.1 `docs/ai/DECISIONS_LOG.md`: add DD103-DD107.
- [x] 7.2 `docs/ai/CURRENT_STATE.md`, `docs/ai/HANDOFF_LATEST.md`, `docs/ai/NEXT_STEPS.md`: refresh.
- [x] 7.3 `docs/ai/sessions/2026-09-19-agent-generated-project-openapi-springdoc.md`: session note.
