# Issue #11 Remote Deployment Governance

Implemented the governance boundary for future VM container deployments without contacting remote infrastructure. The existing local runner was retained unchanged.

- Added managed, tenant-scoped destinations, deployment requests and append-only audit events.
- Added local-only preflight validation, frozen artifact/revision data and OWNER-only one-use confirmation.
- Remote requests truthfully stop at `AUTHORIZED`; there is no executor and no success simulation.
- Added a Generation-tab panel and TypeScript API client for destination selection, preview, confirmation and events.
- Added focused service tests for no-side-effect preview and one-use confirmation.

The local migration `backend_deployments.0002_remote_deployment_governance` is applied. A final audit found that raising an expiry/stale exception inside the confirmation transaction rolled back the intended `FAILED` transition and audit event. `remote_service.confirm` now commits those safe rejection records before responding with the actionable error, which also lets an owner create a fresh request after expiry.

The focused class-level pytest invocation stalled in the constrained Docker environment. Once backend/db were intentionally available, all six remote-governance tests passed individually with `-vv -s --reuse-db` (35–68 seconds each, primarily Django test-database synchronization). The frontend `RemoteDeploymentPanel` test command did not start Vitest because Docker remained creating its temporary no-dependency container for 180 seconds. No global timeout changed. No VM, credentials, SSH or remote Docker action was used.
