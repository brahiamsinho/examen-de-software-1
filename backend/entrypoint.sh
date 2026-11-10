#!/usr/bin/env bash
# Waits for MongoDB to accept connections, applies migrations, then hands
# off to whatever command the compose service / Dockerfile CMD specifies
# (runserver in dev, gunicorn in prod).
set -e

echo "Waiting for MongoDB at ${MONGO_HOST:-mongo}:${MONGO_PORT:-27017}..."

python <<'PYEOF'
import os
import sys
import time

from pymongo import MongoClient
from pymongo.errors import PyMongoError

host = os.environ.get("MONGO_HOST", "mongo")
port = int(os.environ.get("MONGO_PORT", "27017"))
replica_set = os.environ.get("MONGO_REPLICA_SET", "rs0")

max_attempts = 60
for attempt in range(1, max_attempts + 1):
    try:
        # Asking for the primary only succeeds once the replica set is
        # initiated and elected, which is when transactions work.
        client = MongoClient(
            host=host,
            port=port,
            replicaSet=replica_set,
            serverSelectionTimeoutMS=2000,
        )
        client.admin.command("ping")
        client.close()
        print("MongoDB is available.")
        break
    except PyMongoError as exc:
        if attempt == max_attempts:
            print(f"MongoDB never became available: {exc}", file=sys.stderr)
            sys.exit(1)
        time.sleep(1)
PYEOF

echo "Applying database migrations..."
python manage.py migrate --noinput

if python -c "
import django, os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.conf import settings
sys.exit(0 if settings.DEBUG else 1)
"; then
    echo "DEBUG is on: seeding demo data..."
    python manage.py seed_demo
fi

echo "Starting: $@"
exec "$@"