# Remote Deployment Governance

Issue #11 adds governance for generated backends intended for an approved VM. It is separate from the existing local `runner` deployment path.

## Boundary

`RemoteDeploymentDestination` is organization-scoped and stores only a descriptive name, `vm_containers` type, environment, managed configuration identifiers, declared capabilities and enabled state. It deliberately does not contain a host, IP, URL, SSH user, private key, token, password or Docker endpoint.

`RemoteDeploymentRequest` freezes the document revision and SHA-256 of an in-memory generated archive. `RemoteDeploymentEvent` is append-only and records each transition with organization, actor, correlation id, safe error code/message and timestamp. Responses and events omit secrets.

## Flow

1. An authenticated organization member lists server-managed destinations.
2. `POST .../remote-deployments/preview` checks the selected destination and generates the artifact only in memory. It creates no row and makes no network, SSH, Docker or runner call.
3. An `OWNER` requests a remote operation. The server records `AWAITING_CONFIRMATION` and audit event.
4. The same `OWNER` obtains a short-lived one-use proof and confirms it. The backend rechecks membership, destination, document revision and artifact digest inside a transaction.
5. The request reaches `AUTHORIZED`, not `RUNNING`. No real remote executor is enabled in this implementation.

Allowed lifecycle transitions are `DRAFT -> VALIDATED -> AWAITING_CONFIRMATION -> AUTHORIZED -> QUEUED -> DEPLOYING -> RUNNING`, with controlled failure, cancellation and stop exits. The current implementation ends at `AUTHORIZED` until a separately approved executor adapter exists.

## Future VM Authorization

An approved future adapter must be configured server-side with a managed secret reference, least-privilege credentials, an allowlisted target, TLS/authentication, correlation-id logging and an explicit authorization for each action. It must consume only frozen `AUTHORIZED` requests, recheck the state atomically, sanitize returned logs and never accept a host or command from the browser. No credential or VM access was requested or used for Issue #11.
