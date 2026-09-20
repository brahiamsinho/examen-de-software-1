# Gate Evidence: Generated Project OpenAPI via springdoc (DD107)

Date: 2026-09-20. Command: `MSYS_NO_PATHCONV=1 bash scripts/verify-generated-project.sh` (Git Bash, repo root).

## Observed compatibility fact

springdoc 3.1.1 is built on Spring Boot 4.1.0 (parent POM, see `exploration.md`); the
generated project runs on Spring Boot 4.1.1. **Observed on 2026-09-20: it boots green on
Boot 4.1.1 and serves `/v3/api-docs`.** No fix-forward was needed; no Java
`@Configuration` and no `application.yml` key was added.

## Generated `build.gradle` (springdoc line)

    implementation 'org.springdoc:springdoc-openapi-starter-webmvc-api:3.1.1'

Placed after the three Boot starters and before `runtimeOnly 'org.postgresql:postgresql'` (DD104).

Boot jar libraries (`unzip -l build/libs/generated-backend-0.0.1-SNAPSHOT.jar`):

    BOOT-INF/lib/springdoc-openapi-starter-webmvc-api-3.1.1.jar
    BOOT-INF/lib/springdoc-openapi-starter-common-3.1.1.jar
    BOOT-INF/lib/swagger-core-jakarta-2.2.55.jar
    BOOT-INF/lib/spring-boot-4.1.1.jar
    BOOT-INF/lib/spring-webmvc-7.0.9.jar

## Positive run (run 1): exit 0

    BUILD SUCCESSFUL in 46s
    boot-smoke: ready after 6s
    boot-smoke: POST /api/customers -> 201
    boot-smoke: GET /api/customers/<id> -> 200
    boot-smoke: DELETE /api/customers/<id> -> 204
    boot-smoke: GET /api/customers/<id> -> 404
    boot-smoke: GET /v3/api-docs -> 200
    boot-smoke: PASS

The first run was green; the known Maven Central flake did not occur (no rerun was needed).
The gate was re-run after the negative check reverted (run 3): identical result, exit 0,
`BUILD SUCCESSFUL in 43s`, `GET /v3/api-docs -> 200`, `PASS`.

`GlobalExceptionHandler` (`@RestControllerAdvice`) did not break `/v3/api-docs`: 200 with
both needles (`"openapi":` and `"/api/customers"`) present.

Boot log lines seen in the failing run's dump (the boot log is only printed on failure):

    SpringDocAppInitializer  : SpringDoc /v3/api-docs endpoint is enabled by default. ...
    AbstractOpenApiResource  : Init duration for springdoc-openapi is: 304 ms

## Negative check (run 2): exit 7

The `"/api/customers"` needle in the `/v3/api-docs` assertion was temporarily replaced with
`"/api/bogus-fragment"`. Result:

    boot-smoke: GET /v3/api-docs -> 200
    boot-smoke: FAIL: /v3/api-docs does not document /api/customers
    EXIT=7

The new exit code is reachable and distinct from 6 (status). The needle was reverted;
`git diff scripts/boot-smoke.sh` shows only the intended additions and no `bogus` text
remains (`grep -c bogus scripts/boot-smoke.sh` = 0).

## Threat matrix evidence

| Boundary | Evidence |
|---|---|
| Shell argument composition | `/v3/api-docs` is a constant literal through `assert_status`'s argument array; log line `GET /v3/api-docs -> 200`. |
| Response data reaching a command | The body is matched only by bash `case`; the bogus-needle run exits 7 without any body value reaching a URL, variable used in a command or path. |
| Secrets in logs | On the exit-7 path only the capped app log tail was printed (the app log carries no credentials); the body dump (`tail -c 2000`) is only on the exit-6 path and was not triggered. |

## Isolation (Boot Change Isolation)

- `docker compose config --services` unchanged (same set; only listing order varies between runs).
- No `docker compose down` was used; the developer services `backend db frontend mailpit redis` stayed running.
- After every run the `gen-db` container was removed by the gate's cleanup (`docker ps -a | grep -c gen-db` = 0); only the pre-existing `generated_project` volume remains.
