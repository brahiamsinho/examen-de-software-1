#!/usr/bin/env bash
# Waits for Postgres to accept connections, applies migrations, then hands
# off to whatever command the compose service / Dockerfile CMD specifies
# (runserver in dev, gunicorn in prod).
set -e

echo "Waiting for Postgres at ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}..."

python <<'PYEOF'
import os
import sys
import time

import psycopg2

host = os.environ.get("POSTGRES_HOST", "db")
port = os.environ.get("POSTGRES_PORT", "5432")
dbname = os.environ.get("POSTGRES_DB")
user = os.environ.get("POSTGRES_USER")
password = os.environ.get("POSTGRES_PASSWORD")

max_attempts = 60
for attempt in range(1, max_attempts + 1):
    try:
        conn = psycopg2.connect(
            host=host, port=port, dbname=dbname, user=user, password=password
        )
        conn.close()
        print("Postgres is available.")
        break
    except psycopg2.OperationalError as exc:
        if attempt == max_attempts:
            print(f"Postgres never became available: {exc}", file=sys.stderr)
            sys.exit(1)
        time.sleep(1)
PYEOF

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Starting: $@"
exec "$@"
