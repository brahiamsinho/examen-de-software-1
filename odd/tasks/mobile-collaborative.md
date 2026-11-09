# Mobile collaborative app (GitHub #19, without push notifications)
Objective: participate from the phone (log in, organizations, AI chat, approve/reject AI proposals, see diagram changes). Branch: `feature/mobile-collaborative`. Delivery: `ask-on-risk` (push and PR only with the user's authorization). Runners: backend `docker compose run --rm backend pytest <path>`; mobile `C:\Users\brahi\flutter\bin\flutter.bat test` and `analyze` in `mobile/`.

## Specs
- S1: "Se puede aprobar o rechazar una propuesta desde el celular." Uses the existing `POST .../ai-proposals/{id}/approve` and `/reject`; OWNER/EDITOR decide, VIEWER only reads.
- S2: The phone logs in and sees only the user's own organizations and diagrams. Another organization's data answers 404, as on the web. (Assumption: a bearer token is the mobile credential, because the web uses cookies plus CSRF.)
- S3: "chat con la IA, aprobar o rechazar propuestas y ver cambios del diagrama" — chat via `GET/POST .../chat` (the AI answers when the message mentions `@IA`); diagram changes are read from the session log (`GET .../log`). VIEWER reads only. "Fuera de alcance: edición completa del canvas."
- S4: "Funciona con conexión inestable, con reintentos y estado claro." Retries only for safe reads; a write is never silently repeated; the screen always shows loading / offline / error / retry state.
- S5: OUT OF SCOPE NOW (user: "las notificaciones push la vemos despues tengo credenciales de firebase"): "Llega una notificación cuando hay una propuesta o un cambio en un diagrama de la organización." and "Solo se notifica a miembros de esa organización." Firebase credentials never go in the repository, the code or this document.
- S6 (assumption): the mobile token is opaque, only its SHA-256 hash is stored, it expires (30 days), it is revocable (logout), and it is accepted on the same routes as the session cookie without CSRF (a bearer header is not sent automatically by a browser).

## Tasks
- [ ] T1 (S2, S6) Backend bearer-token auth: model + `POST /api/auth/mobile-token` + revoke + middleware. Route: inline. Risk: item 2 (auth) → independent verifier. Commit: pending.
- [ ] T2 (S2, S4) Mobile foundation: secure token storage, API client with bearer, retry/connection state, login screen. Route: inline. Commit: pending.
- [ ] T3 (S2) Mobile organizations and diagrams list. Route: inline. Commit: pending.
- [ ] T4 (S3, S4) Mobile diagram screen: changes (log) and AI chat. Route: inline. Commit: pending.
- [ ] T5 (S1, S4) Mobile AI proposals: list, approve, reject. Route: inline. Commit: pending.
- [ ] T6 Docs and project memory (`docs/ai/*`). Route: inline. Commit: pending.

## Log
- L1 (2026-11-08, user): "si, la 19, las notificaciones push la vemos despues tengo credenciales de firebase"
- L2 (2026-11-08, explorer handoff, verified against source): every router uses `Router(auth=django_auth)`; ninja's `SessionAuth` (django_auth) runs a CSRF check in `_get_key` unless `request._ninja_csrf_exempt` is set, then reads `request.user`; `resolve_membership` uses `request.user`; PyJWT is in requirements but unused; the document WebSocket authenticates by session cookie and checks Origin (not touched here); `flutter_secure_storage` is not a dependency; `AppConfig.apiBaseUrl` exists but nothing uses it.
- L3 (design decision): authenticate with a Django middleware that sets `request.user` from a valid `Authorization: Bearer` header and marks the request CSRF-exempt, so no router changes. An invalid or expired token leaves the request anonymous (401 from `django_auth`).
- L4 (decision): no WebSocket for the phone in this slice; changes come from the log with pull-to-refresh. Revisit with push notifications.
