# 2026-11-08 - Issue #19: mobile collaborative app (no push)

Goal: participate from the phone (login, organizations, AI chat, approve or reject AI proposals, see changes). Push notifications deferred by the user, who holds the Firebase credentials (never to be committed).

Commits on `feature/mobile-collaborative`:
- `033afe1` feat(auth): bearer-token login for the API (high risk: auth; independently verified, no blockers)
- `4ac233f` test(auth): pin the scope and smuggling cases the verifier suggested
- `6166007` feat(mobile): sign in with a bearer token (secure storage, API client, login, gate)
- `100145a` feat(mobile): list organizations and diagrams (reusable `RemoteData`)
- `ce2874f` feat(mobile): chat with the AI and see diagram changes
- `c7c6e24` feat(mobile): approve or reject AI proposals from the phone

Checks: backend 1692 passed; `flutter test` 197 passed; `flutter analyze` clean; a throwaway end-to-end backend test confirmed the real API matches the Flutter parsers.

Lessons:
- An invalid bearer token must be a 401 on every method, or an expired token looks like a 403 CSRF/role error on writes.
- Writes are never retried automatically; a timeout does not tell whether the server applied them.
- In Flutter widget tests, `enterText` does not pump a frame, so a button that depends on the field only enables after `pump()`.
- `flutter pub add` on Windows prints a symlink warning (Developer Mode off) but still succeeds; only desktop plugin builds need it.

Open: real device run, push notifications, WebSocket for the phone, PR with `Refs #19`.
