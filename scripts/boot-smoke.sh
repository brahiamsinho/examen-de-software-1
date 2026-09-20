#!/usr/bin/env bash
# Boot smoke for the generated Spring project (generated-project-boot-smoke).
#
# Runs INSIDE the `jvm-boot-smoke` compose service (working directory is the
# generated project, /scripts is this folder mounted read-only). It boots the
# non-plain bootJar against the throwaway `gen-db`, waits for readiness and
# drives one CRUD round-trip on /api/customers over container loopback.
# No container path is hardcoded here: the working directory comes from compose.
#
# The literals below (path, request key, statuses) are pinned by
# backend/apps/generation_runner/tests/test_boot_smoke_contract.py.
#
# Exit codes: 0 pass | 2 build/libs missing | 3 zero or several boot jars
#             4 JVM exited before ready | 5 readiness timeout
#             6 HTTP status mismatch, or id absent/malformed
set -euo pipefail

BASE_URL=${SMOKE_BASE_URL:-http://127.0.0.1:${SERVER_PORT:-8080}}
READY_TIMEOUT=${SMOKE_READY_TIMEOUT:-180}
POLL_INTERVAL=2
APP_LOG=${TMPDIR:-/tmp}/boot-smoke-app.log
BODY=${TMPDIR:-/tmp}/boot-smoke-body.txt
APP_PID=""
HTTP_STATUS=000

log() { echo "boot-smoke: $*"; }
die() { local code=$1; shift; echo "boot-smoke: FAIL: $*" >&2; exit "$code"; }

# Stop the JVM and, on failure only, show the app log (never the environment:
# it carries the database password).
cleanup() {
  local rc=$?
  trap - EXIT
  if [ -n "$APP_PID" ] && kill -0 "$APP_PID" 2>/dev/null; then
    kill "$APP_PID" 2>/dev/null || true
    wait "$APP_PID" 2>/dev/null || true
  fi
  if [ "$rc" -ne 0 ] && [ -f "$APP_LOG" ]; then
    # A stack trace can push the root cause out of the tail, so list it first.
    echo "--- root causes (FATAL / Caused by) ---" >&2
    grep -E 'FATAL|Caused by' "$APP_LOG" | tail -n 5 >&2 || true
    echo "--- app log (last 60 lines) ---" >&2
    tail -n 60 "$APP_LOG" >&2 || true
  fi
  exit "$rc"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# The single network call site (DD99). Sets HTTP_STATUS; returns non-zero when
# curl itself fails (connection refused, timeout). Arguments are an array: no
# eval, no sh -c.
_http() {
  local method=$1 path=$2 json=${3:-}
  local -a args=(-sS --max-time 10 -o "$BODY" -w '%{http_code}' -X "$method")
  if [ -n "$json" ]; then
    args+=(-H 'Content-Type: application/json' -d "$json")
  fi
  HTTP_STATUS=$(curl "${args[@]}" "$BASE_URL$path") || { HTTP_STATUS=000; return 1; }
}

assert_status() {
  local expected=$1 method=$2 path=$3 json=${4:-}
  if ! _http "$method" "$path" "$json" || [ "$HTTP_STATUS" != "$expected" ]; then
    echo "--- response body ---" >&2
    tail -c 2000 "$BODY" >&2 2>/dev/null || true
    echo >&2
    die 6 "$method $path expected $expected, got $HTTP_STATUS"
  fi
  log "$method $path -> $HTTP_STATUS"
}

# 1. Resolve the boot jar: skip *-plain.jar, require exactly one survivor (DD97).
[ -d build/libs ] || die 2 "build/libs is missing: the compile step did not run"
JAR=""
JAR_COUNT=0
for candidate in build/libs/*.jar; do
  [ -e "$candidate" ] || continue
  case $candidate in *-plain.jar) continue ;; esac
  JAR=$candidate
  JAR_COUNT=$((JAR_COUNT + 1))
done
[ "$JAR_COUNT" -eq 1 ] || die 3 "expected exactly one boot jar in build/libs, found $JAR_COUNT"
log "jar=[$JAR]"

# 2. Launch in the background.
java -jar "$JAR" >"$APP_LOG" 2>&1 &
APP_PID=$!

# 3. Readiness: /count proves context + datasource + ddl-auto table (DD98).
START=$SECONDS
until _http GET /api/customers/count 2>/dev/null && [[ $HTTP_STATUS == 2* ]]; do
  if ! kill -0 "$APP_PID" 2>/dev/null; then
    die 4 "the JVM exited before becoming ready"
  fi
  if [ $((SECONDS - START)) -ge "$READY_TIMEOUT" ]; then
    die 5 "not ready after ${READY_TIMEOUT}s"
  fi
  sleep "$POLL_INTERVAL"
done
log "ready after $((SECONDS - START))s"

# 4-8. CRUD round-trip.
assert_status 201 POST /api/customers '{"fullName":"boot-smoke"}'

# Pure-bash id extraction (DD100): no jq in the image; validate the shape before
# the value reaches any URL.
RESPONSE=$(<"$BODY")
RESPONSE=${RESPONSE//[[:space:]]/}
case $RESPONSE in
  *'"id":"'*) ;;
  *) die 6 "the create response carries no id" ;;
esac
REST=${RESPONSE#*'"id":"'}
CUSTOMER_ID=${REST%%'"'*}
[[ $CUSTOMER_ID =~ ^[0-9a-fA-F-]{36}$ ]] || die 6 "the created id is not UUID-shaped"
log "created id=[$CUSTOMER_ID]"

assert_status 200 GET "/api/customers/$CUSTOMER_ID"
assert_status 204 DELETE "/api/customers/$CUSTOMER_ID"
assert_status 404 GET "/api/customers/$CUSTOMER_ID"

log "PASS"
