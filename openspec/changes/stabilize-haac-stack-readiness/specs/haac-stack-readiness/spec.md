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
