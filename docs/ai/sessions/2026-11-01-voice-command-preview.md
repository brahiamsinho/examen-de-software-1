# Voice command preview — 2026-11-01

Voice commands now create an expiring preview plan rather than immediately
changing a diagram. The browser presents the recognized changes and only the
explicit apply action sends confirmation.

The plan is bound to organization, document and revision. Confirmation checks
that revision inside the document row lock before applying the complete command
batch atomically. Class deletion is now a supported voice command because it
is protected by this confirmation step.

Verification: backend 242 focused tests and frontend 430 tests passed. An
independent high-risk verifier found no blockers.
