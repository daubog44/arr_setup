## Design

### Control Plane

The reconciler uses the internal Litmus services already present in the cluster:

- `litmus-auth-server-service` for admin login and project discovery
- `litmus-server-service` for GraphQL mutations and queries

It operates through the existing `cluster_session(...)` and `kubectl_port_forward(...)` helpers, so it does not mutate the workstation kubeconfig and it stays compatible with LAN and Tailscale access.

### Flow

1. Reconcile Litmus admin credentials with the existing `reconcile_litmus_admin(...)` path.
2. Log in to Litmus auth and fetch:
   - bearer token
   - default project ID
3. Query `listEnvironments(projectID)`:
   - if `haac-default` exists, use it
   - else if a legacy `test` environment exists, reuse it to avoid duplicating environments
   - else create `haac-default` with `createEnvironment(...)`
4. Query `listInfras(projectID)` for the selected environment:
   - if an infra in that environment is already active and confirmed, stop
   - if stale `haac-default` infra records exist but are inactive, delete them
5. Register a new default infra with `registerInfra(...)` using the internal frontend URL as the required `Referer`.
6. Apply the returned `manifest` directly to the cluster with `kubectl apply -f -`.
7. Wait for the `litmus` namespace agent deployments to become ready.
8. Poll `listInfras(projectID)` until the target infra is active and confirmed.

### Idempotence

- healthy active infra: no-op
- stale inactive default infra: delete and recreate
- legacy manually-created `test` environment: reuse rather than duplicating

### Verification

- CLI verification is authoritative: the bootstrap fails if Litmus still requires manual infrastructure deployment
- browser verification remains a secondary UX check
