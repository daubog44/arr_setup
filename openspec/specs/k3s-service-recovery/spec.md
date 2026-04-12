# k3s-service-recovery Specification

## Purpose
TBD - created by archiving change bound-k3s-service-restarts. Update Purpose after archive.
## Requirements
### Requirement: K3s service recovery is bounded during node configuration

The system MUST not wait indefinitely when `configure-os` needs to restart or reload `k3s` or `k3s-agent`.

#### Scenario: Worker service recovery hangs

- **WHEN** node configuration restarts or reloads `k3s-agent` on a worker and the service does not return to `active` within the configured recovery window
- **THEN** the bootstrap MUST fail `Node configuration` with explicit service diagnostics instead of hanging indefinitely
- **AND** the failure output MUST include enough service-state evidence to distinguish a K3s recovery problem from a later GitOps or workload issue

### Requirement: Healthy K3s recovery still proceeds automatically

The system MUST preserve the normal rerun path when K3s services recover within the expected window.

#### Scenario: Service becomes active in time

- **WHEN** `configure-os` restarts or reloads `k3s` or `k3s-agent` and the service returns to `active` before the recovery window expires
- **THEN** the rerun MUST continue automatically without requiring manual operator steps

