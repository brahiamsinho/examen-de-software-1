# Examen-1-Software

Full-stack template project (exam/learning context): Django + Django REST
Framework backend, PostgreSQL database, Next.js (TypeScript, App Router)
frontend, and a Flutter mobile app — backend and frontend run in Docker,
mobile runs on the host/emulator.

> **Note on env files:** the sandbox that generated this scaffold blocks
> writing any file with `.env` in its path, so every example env file
> below was written without the leading dot (`env.example` instead of
> `.env.example`). Rename each one as shown before use.

## Prerequisites

- Docker + Docker Compose (backend, frontend, database)
- Flutter SDK 3.44+ (mobile app; not dockerized)
- Node/npm are only needed on the host if you want to run the frontend
  outside Docker — otherwise the `frontend` container handles it.

## Quickstart

1. Copy every env example to its real file:

   ```
   cp env.example .env
   cp backend/env.example backend/.env
   cp frontend/env.local.example frontend/.env.local
   ```

   Then edit the copies with real values (never commit the `.env` files —
   they're gitignored).

2. Build and start the stack:

   ```
   docker compose up --build
   ```

3. Reach the apps:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000

## Session auth deployment note

Protected frontend routes (`/dashboard`, `/select-organization`) are
validated **server-side** on every request, not only client-side: the
Next.js server itself calls the Django API (`INTERNAL_API_URL`, defaulting
to `http://backend:8000` inside Docker Compose) to check the session cookie
before rendering. This only works when the browser sends the Django
`sessionid` cookie to the Next.js origin — true for `localhost` and any
same-parent-domain deploy. A split-domain deployment (frontend and backend
on unrelated domains) would bounce every authenticated user to `/login`;
see `docs/ai/ARCHITECTURE.md`'s "Route protection" section before deploying
that way.

## Backend management commands

Run any `manage.py` command inside the running `backend` container:

```
docker compose exec backend python manage.py <command>
```

Examples: `migrate`, `createsuperuser`, `startapp <name> apps/<name>`.

## Mobile (Flutter)

Not dockerized — run it against a device/emulator on the host, pointing
it at wherever the backend is reachable:

```
cd mobile
flutter run --dart-define=API_BASE_URL=http://localhost:8000
```

(Android emulators should generally use `http://10.0.2.2:8000` instead of
`localhost` — see `mobile/lib/core/config/app_config.dart`.)

## Everyday Docker Compose commands

```
docker compose ps               # list running services
docker compose logs -f <service>  # tail logs (e.g. backend, frontend, db)
docker compose exec <service> sh  # shell into a running container
docker compose down             # stop and remove containers
```

## Project layout

```
backend/   Django + DRF project (config/ settings package, apps/ for future features)
frontend/  Next.js + TypeScript app (App Router, src/ dir)
mobile/    Flutter app
docs/ai/   living project memory (vision, architecture, decisions, state)
```

See `docs/ai/` for architecture notes, tech stack rationale, decisions
log, and current state.
