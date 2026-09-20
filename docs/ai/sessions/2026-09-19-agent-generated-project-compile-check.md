# Session Note: generated-project compile check (apply)

Date: 2026-09-19
Change: `generated-project-compile-check` (§37 item 13, slice 2 of 3). State: applied, verified (PASS WITH WARNINGS, 0 critical) and archived at `openspec/changes/archive/2026-09-19-generated-project-compile-check/`; the commit is what remains.

## Summary

`sdd-apply` implemented all 42 tasks (Strict TDD for the Python half, single PR under `size:exception`) in two batches. Batch 1 (phases 1-4) built `backend/apps/generation_runner/`: the pure `write_sources` writer and typed errors, the Protocols, the CLI, `runner_image.py` and the sample model. Batch 2 (phases 5-8) added the compose/script harness, resolved the "To Confirm at Apply" items empirically, ran the manual gate and updated docs.

## Gate (manual, compose-based, not in pytest)

- Command (repo root, Git Bash): `bash scripts/verify-generated-project.sh`
- Resolved image: `gradle:9.7.1-jdk21`. Result: `BUILD SUCCESSFUL in 47s`, exit 0 (second run 43 s, exit 0). 41 generated files in the named volume `generated_project`.
- Full evidence and the negative checks 7.2-7.4: `openspec/changes/generated-project-compile-check/gate-evidence.md`.

## Tests

`docker compose exec -T backend pytest -q` = 822 passed (764 before + 58 new in `apps/generation_runner`; 56 at apply time plus 2 CLI tests added after verify). `apps/spring_generator` = 317 passed, unmodified. Isolation: no `jvm` marker in `backend/pyproject.toml`, no `docker.sock` in the compose file, no version literal in `apps/generation_runner/`, compose or the script.

## Deviations from design.md

1. `${GRADLE_IMAGE:?}` broke every ordinary compose command (`config`, `exec`, `ps`) while the variable was unset. Fallback: sentinel default `gradle.invalid/unset:GRADLE_IMAGE-not-set-...` that fails at pull time naming `GRADLE_IMAGE`. Check 7.2 became "pull failure naming it".
2. The backend dev image has no source, so `generate-project` needed `./backend:/app:ro` (first gate run failed with `ModuleNotFoundError: No module named 'apps'`).
3. The script keeps `--no-deps -T` and `tr -d '\r'` defensively although the raw tag output was already clean.

## Things to know

- Symlink-escape test seam: DD78 step 1 refuses any non-empty target, so a real pre-existing symlink is unreachable through `write_sources`. Step 4 is tested via `_reject_escaping_paths` with a real symlink plus an end-to-end test monkeypatching `filesystem._resolve`.
- Verify warning W2 (fixed after verify, Strict TDD): the CLI used to catch only `(GeneratedSourceWriteError, ValueError)`, so a generator `UngeneratableSourceError` or an `OSError` showed a traceback. It now also catches both and prints `error: ...` with exit 1.
- Accepted warnings: W1 (sentinel default instead of `${GRADLE_IMAGE:?}`, amended in the merged spec), W3 (no recorded failing `generate-project` run), W4 (gate needs live Maven Central; one transient TLS flake seen, rerun green), W5 ("default up unaffected" checked via `config`, not a real `up`).
- Docker leftovers by design: named volume `examen-1-software_generated_project`, image `examen-1-software-generate-project`, pulled `gradle:9.7.1-jdk21`, one stopped `generate-project-1` container replaced on the next run. No `down` is used because it would stop `db`/`redis`.
- `.gradle/` added to `.gitignore`; `git status` shows no `build/`/`.gradle/` leaking into the repo.

## Next

Commit (never `.pi/`); then slice 3 `generated-project-boot-smoke` and the queued `inheritance_context.py:169` bugfix (switch the sample model to `new_id()` when fixed).
