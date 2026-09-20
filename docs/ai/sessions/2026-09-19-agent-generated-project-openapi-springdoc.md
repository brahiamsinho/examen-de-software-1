# Session: generated-project-openapi-springdoc (apply)

Executed 2026-09-20 (file dated 2026-09-19 per the change plan). State: verified PASS WITH WARNINGS (0 CRITICAL, 3 warnings, 4 suggestions) and archived at `openspec/changes/archive/2026-09-20-generated-project-openapi-springdoc/`.

## What was done

- Strict TDD: baseline 389 (`apps/spring_generator` + `apps/generation_runner`); RED (collection `ImportError` for `SPRINGDOC_VERSION`, missing coordinate in the generated `build.gradle`); GREEN 393.
- `emit/versions.py` (`SPRINGDOC_VERSION`), `emit/scaffold_context.py` (last field `springdoc_version`), `emit/renderer.py` (forwards it), `build.gradle.j2` (springdoc starter line).
- `scripts/boot-smoke.sh`: `GET /v3/api-docs` -> 200 plus two pure-bash needles; exit 7 for body mismatch, exit 6 for non-200; header exit-code table updated.
- Gate: `bash scripts/verify-generated-project.sh` exit 0 on the first run; negative check (bogus needle) exit 7, reverted, gate re-run green.

## Findings

- springdoc 3.1.1 (built on Boot 4.1.0) runs on Boot 4.1.1; the generated `@RestControllerAdvice` did not break `/v3/api-docs`; no fix-forward.
- One own test bug caught during GREEN: `count("springdoc")` matches the coordinate twice; fixed to `count("springdoc-openapi")`.
- The exit-7 path prints no response body (only the app log tail); the body dump is on the exit-6 path.

## Totals

Backend 840, `apps/spring_generator` 325, `apps/generation_runner` 68. Nothing committed; `.pi/` untouched.

## Next

Commit (never `.pi/`). Then §37 items 15-16 (Postman collection, Domain Manifest).
