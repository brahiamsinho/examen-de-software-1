# Gate Evidence: spring-generator-inheritance-subclass-naming

Task 5.1 / 5.2 (DD91). Manual end-to-end compile gate over the uuid4-hex class-id sample model.

- Date: 2026-09-19
- Command: `bash scripts/verify-generated-project.sh` (Git Bash, repo root; read-only script)
- Resolved `GRADLE_IMAGE`: `gradle:9.7.1-jdk21`
- Sample model: `backend/apps/generation_runner/samples/sample_model.py` with frozen uuid4-hex class ids (vehicle/car/truck digit-leading)

## Run 1 (transient infrastructure failure, not a code failure)

- Exit code: `1`
- Final Gradle line: `BUILD FAILED in 57s`
- Cause: `:compileJava` could not download `jackson-databind-3.1.5.jar` from Maven Central: `Could not HEAD ... The server may not support the client's requested TLS protocol versions ... Remote host terminated the handshake`. Dependency-resolution flake; no Java compile error was reported.

## Run 2 (immediate rerun, no change in between)

- Exit code: `0`
- Final Gradle line: `BUILD SUCCESSFUL in 41s` (`5 actionable tasks: 5 executed`)
- `:compileJava`, `:jar`, `:assemble`, `:build` all executed; the generated `Car.java` / `Truck.java` compile although their element ids start with a digit.

## Result

PASS on run 2. Working tree impact of the gate: none (`git status` shows only the intended source/test edits).
