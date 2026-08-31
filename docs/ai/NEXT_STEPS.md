# Next Steps

1. Define the first real Django app under `backend/apps/` once business
   requirements exist (e.g. `backend/apps/<feature>/`), register it in
   `INSTALLED_APPS`.
2. Add DRF serializers and viewsets for that app's models, wire them into
   `backend/config/urls.py` (e.g. via a router).
3. Connect the Next.js frontend to the API through `src/lib/api.ts`,
   building real pages/components under `frontend/src/app/`.
4. Design and build real Flutter screens under `mobile/lib/`, replacing
   the default counter-app template, using `AppConfig.apiBaseUrl` for all
   network calls.
5. Add authentication (e.g. DRF token/session auth or JWT) once there is
   a real user model / login flow to support, and thread it through both
   the Next.js and Flutter clients.
6. Rename the `env.example` files to their dotfile form and run
   `docker compose up --build` end-to-end to validate the stack actually
   builds and boots (not yet done in this scaffold).
