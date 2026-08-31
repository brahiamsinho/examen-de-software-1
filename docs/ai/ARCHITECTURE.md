# Architecture

## Top-level layout

```
backend/   Django + DRF project
frontend/  Next.js + TypeScript project
mobile/    Flutter project
docs/ai/   persistent living project memory
```

Each top-level directory is an independently buildable/runnable unit with
its own dependency manifest, Dockerfile (except mobile), and env
configuration. This is "modular by default" per project convention:
nothing is shared across `backend/`, `frontend/`, and `mobile/` except the
HTTP contract between them (the Django API), and that contract is only
reached through explicit environment variables (`CORS_ALLOWED_ORIGINS` on
the backend, `NEXT_PUBLIC_API_URL` on the frontend, `API_BASE_URL` dart-define
on mobile) — never hardcoded hosts.

## Backend structure

- `backend/config/` — the Django settings package (settings, root urlconf,
  WSGI/ASGI entrypoints). This is project-wide wiring only.
- `backend/apps/` — the intended home for every future Django feature app.
  It is currently empty (only `__init__.py` + a README) because no
  business requirements have been defined yet. Convention: one app per
  bounded feature, each with its own models/serializers/views/urls,
  registered into `INSTALLED_APPS` and included from `config/urls.py`.

## Environment-driven configuration

Nothing is hardcoded: secrets, hosts, database credentials, and CORS
origins are all read from environment variables (via `django-environ` on
the backend, `process.env.NEXT_PUBLIC_API_URL` on the frontend behind a
single `src/lib/env.ts` helper, and `--dart-define=API_BASE_URL` on
mobile). In Docker Compose, the backend reaches Postgres via the service
name `db`, never `localhost`.
