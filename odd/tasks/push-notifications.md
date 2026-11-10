# Push notifications for the mobile app (GitHub #19)
Branch: feat/push-notifications. Strategy: ask-on-risk. Runner: pytest in docker (backend), flutter test (mobile).

## Specs
- S1: "Llega una notificación cuando hay una propuesta o un cambio en un diagrama de la organización."
- S2: "Solo se notifica a miembros de esa organización." Membership is re-checked when sending, not when the device registered.
- S3: "Funciona con conexión inestable, con reintentos y estado claro." Sending retries with backoff and never breaks the request that triggered it.
- S4: Credentials never in the repo (`backend/secrets/` is git-ignored; path comes from `FIREBASE_CREDENTIALS_PATH`). Without it, sending is a no-op.
- S5: The mobile app registers its device token after login and removes it on logout.
- Assumption: a diagram-change push is limited to one per diagram per minute to avoid spam.
- Known blocker for mobile: `google-services.json` is for package `com.example.mobile`, the app is `com.examen.software.mobile`. User chose to leave it; the Android build with the Google services plugin will fail until they match.

## Tasks
- T1 (S4,S5): `notifications` app, `DeviceToken` model, register/unregister API. Route: inline.
- T2 (S1-S4): FCM sender, org-scoped fan-out, triggers on proposal and document change. Route: inline.
- T3 (S5): mobile registers/removes the token (blocked by the package mismatch).

## Log
- L1 (2026-11-10, user): "subilo y despues haremos las notificaciones push con las credenciales que te pasare enseguida"
- L2 (2026-11-10, user): "dejemoslo asi, no nos comamos la cabeza si funciona pa que tocarlo" (about the package mismatch)