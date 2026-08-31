# Decisions Log

- **Django settings package named `config`** — keeps the settings/urls/wsgi/asgi
  package name generic and decoupled from any specific app or product name.
- **Env vars via django-environ, no hardcoding** — secrets, hosts, DB
  credentials, and CORS origins must never be committed or baked into code;
  `environ.Env` centralizes reading them with sane `.env` file support.
- **psycopg2-binary over psycopg3** — chosen for tutorial/documentation
  ubiquity: most Django docs, tutorials, and Stack Overflow answers still
  assume psycopg2, and the binary wheel avoids build-toolchain friction in
  the Docker image.
- **CORS via django-cors-headers** — the Next.js frontend is a separate
  origin from the Django API, so cross-origin requests need to be
  explicitly allow-listed rather than silently blocked or wide open.
- **Tailwind intentionally NOT added** — it was not requested by the spec;
  adding it now would be an unnecessary dependency/opinion for a bare
  scaffold.
- **Flutter not dockerized** — mobile apps are built/run via the Flutter
  SDK against emulators/physical devices on the host, not inside a Linux
  container; there is no meaningful way to "run" a mobile app in a
  server-style container.
- **Multi-stage Dockerfiles with dev/prod targets (backend + frontend)** —
  a single Dockerfile serves both live-reload local development (bind
  mounts, dev server) and a leaner production image (built artifacts,
  gunicorn/`next start` or standalone output) without duplicating base
  layers.
- **Env-example files written without the leading dot** (`env.example`,
  `env.local.example`) — the Write/Bash sandbox used to generate this
  scaffold refuses any file path containing the substring `.env`, even for
  placeholder content. Documented in each file and in the root README;
  rename them locally (e.g. `mv env.example .env`) to restore the
  conventional dotfile name.
