#!/usr/bin/env bash
# Compile + boot gate for the generated Spring project
# (generated-project-compile-check, generated-project-boot-smoke).
#
# Generates the sample project into the named volume `generated_project`, runs
# `gradle build` on it inside the Gradle image whose tag is derived from
# backend/apps/spring_generator/emit/versions.py (no version literal here), then
# boots the jar against a throwaway Postgres and runs one CRUD round-trip
# (scripts/boot-smoke.sh).
#
# Usage (Git Bash, repo root):  bash scripts/verify-generated-project.sh
# Exit 0 means BUILD SUCCESSFUL and the smoke passed. Negative case:
#   GEN_DB_PASSWORD=wrong bash scripts/verify-generated-project.sh
set -euo pipefail

# Git Bash rewrites container-looking paths; keep them untouched. All container
# paths live in docker-compose.yml, none are passed inline from here.
export MSYS_NO_PATHCONV=1

cd "$(dirname "$0")/.."

# Compose interpolates the WHOLE file before starting any service. Without a
# value, jvm-verify's image falls back to an unpullable sentinel; this run
# passes a throwaway value so nothing depends on that, and that image is never
# pulled because jvm-verify is not started here.
GRADLE_IMAGE="$(
  GRADLE_IMAGE=gradle:bootstrap docker compose run --rm --no-deps -T generate-project \
    python -c "from apps.generation_runner.runner_image import gradle_runner_image; print(gradle_runner_image())" \
    | tr -d '\r' | tail -n 1
)"

if [ -z "$GRADLE_IMAGE" ]; then
  echo "verify-generated-project: could not resolve GRADLE_IMAGE" >&2
  exit 1
fi

echo "verify-generated-project: GRADLE_IMAGE=[$GRADLE_IMAGE]"
export GRADLE_IMAGE

# `run` never stops its dependencies, so gen-db would outlive the gate. Remove
# only that service (compose-scoped, literal name), never `down`: that would
# stop the developer's db/redis/backend (DD95). An EXIT trap keeps $?.
cleanup() {
  docker compose --profile jvm-verify rm -sfv gen-db >/dev/null 2>&1 || true
}
trap cleanup EXIT

# Two sequential steps (not depends_on) so a Gradle failure keeps its own output
# and `set -e` stops the gate before the smoke (DD94).
docker compose --profile jvm-verify run --rm jvm-verify
docker compose --profile jvm-verify run --rm jvm-boot-smoke
