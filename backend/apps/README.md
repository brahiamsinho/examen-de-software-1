# backend/apps/

This package is the intended home for future Django feature apps
(e.g. `backend/apps/accounts/`, `backend/apps/orders/`, ...).

No business requirements have been defined yet, so no app lives here
at scaffold time. When a real feature is ready to be built:

1. Create a new app with `docker compose exec backend python manage.py startapp <name> apps/<name>`.
2. Add `"apps.<name>"` to `INSTALLED_APPS` in `backend/config/settings.py`.
3. Wire its URLs into `backend/config/urls.py`.

This keeps `config/` limited to project-wide wiring (settings, root
urlconf, WSGI/ASGI) and every feature isolated under its own app
package, per the project's "modular by default" convention.
