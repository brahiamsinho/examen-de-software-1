# Tech Stack

| Technology | Justification |
|---|---|
| Django 5 (>=5.0,<5.1) | Batteries-included Python web framework; modern 5.x layout requested. |
| Django REST Framework | Standard, well-documented way to expose a JSON API from Django. |
| django-environ | Reads all config from environment variables — no hardcoded secrets/hosts. |
| psycopg2-binary | PostgreSQL driver; binary build chosen over building psycopg3 from source for tutorial/documentation ubiquity and zero-fuss Docker builds. |
| django-cors-headers | Frontend (Next.js) is a separate origin from the API; this handles CORS correctly. |
| PostgreSQL 16 (alpine image) | Production-grade relational database, matches `POSTGRES_*` env vars used by both the `db` compose service and Django settings. |
| Next.js (latest) + TypeScript + App Router | Modern React framework with file-based routing, SSR/SSG, and first-class TypeScript support. |
| Flutter 3.44 | Single codebase for cross-platform mobile (and beyond) client. |
| Docker / Docker Compose | Reproducible dev environment; `backend` and `frontend` each get dev/prod Dockerfile targets, `db` is a standard Postgres image. |
