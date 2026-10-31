# Image reconciliation — 2026-10-31

Image imports now produce a preview plan instead of writing immediately.
The confirmation dialog lists planned changes and only its explicit action
persists the reconciliation.

Plans are tenant/document-bound and expire after 15 minutes. Confirmation
checks the base revision inside the document's row lock and applies the
validated command batch atomically, preventing stale plans from deleting
newer edits.

Verification: backend 237 focused tests and frontend 430 tests passed.
An independent high-risk verifier found the legacy direct-write route and a
stale-plan race; both were corrected and rechecked.
