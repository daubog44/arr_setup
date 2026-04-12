## ADDED Requirements

### Requirement: GPU runtime class selection is centralized for NVIDIA workloads

The chart MUST define one shared NVIDIA runtime class value and reuse it across tracked NVIDIA workloads and runtime-dependent support components.

#### Scenario: NVIDIA device plugin uses the shared runtime class

- **GIVEN** the cluster exposes a `RuntimeClass` for the NVIDIA runtime handler
- **WHEN** the chart renders the `nvidia-device-plugin` DaemonSet
- **THEN** the DaemonSet template MUST set `runtimeClassName` from the shared GPU scheduling values

#### Scenario: Jellyfin uses the same shared runtime class

- **GIVEN** Jellyfin is the tracked NVIDIA workload in the stack
- **WHEN** the chart renders the Jellyfin Deployment
- **THEN** the Deployment template MUST use the same shared NVIDIA runtime class value

### Requirement: Gateway listeners match the active Traefik entrypoint contract

The stack Gateway MUST use listener ports that Traefik can accept with the bundled K3s deployment configuration.

#### Scenario: Gateway listener is accepted by Traefik

- **GIVEN** the platform uses the bundled K3s Traefik deployment with the `web` entrypoint on `8000`
- **AND** public TLS is terminated upstream by Cloudflare rather than by the in-cluster Gateway
- **WHEN** the `haac-gateway` resource is reconciled
- **THEN** Traefik MUST accept the Gateway instead of reporting `PortUnavailable` or invalid TLS configuration

### Requirement: The stack MUST avoid non-standard Headlamp bootstrap resources that block reconciliation

Headlamp configuration in the stack MUST rely on the standard in-cluster deployment path instead of extra bootstrap resources that keep the workload app from reconciling.

#### Scenario: Headlamp stack resources no longer depend on a bootstrap token-header workaround

- **GIVEN** Headlamp already runs with `serviceAccountName: headlamp-admin` in-cluster
- **WHEN** `haac-stack` reconciles
- **THEN** the chart MUST NOT require a separate `headlamp-token-bootstrap` Job or `headlamp-token-header` route middleware to treat the stack as converged
