# 2026-11-09 - MongoDB migration of Modelia's own database

Branch `feature/mongodb-migration` (from `main` at `2151d61`). Feature doc: `odd/tasks/mongodb-migration.md`.

## Goal
User request: move Modelia's own database to MongoDB; the Spring backend Modelia generates stays as it is. No data to keep.

## What was done
- Django 5.2 + `django-mongodb-backend`; `mongo` compose service (single-node replica set); regenerated migrations; ObjectId ids.
- Row locks replaced by `config/transactions.py` (retry on MongoDB write conflicts, `touch` for guard rows).
- Web and Flutter read chat/log/event ids as strings; login lowercases the email.
- Production compose, `env.example` and `deploy/README.md` updated.

## Evidence
- Backend 1700 passed (+ concurrency tests); web tsc clean, 554 Vitest; Flutter 201 passed, analyze clean.
- Mutation check: without `touch`, two owners demoting each other at once leave zero owners; the test catches it.
- Real stack on Mongo: seed, login, create diagram, chat, log, other organization 404.

## Open
- Independent verification of the high-risk change; EC2 rehearsal; PR only with user authorization.
