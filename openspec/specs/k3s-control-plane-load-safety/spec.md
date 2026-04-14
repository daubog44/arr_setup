# k3s-control-plane-load-safety Specification

## Purpose
TBD - created by archiving change stabilize-k3s-control-plane-load. Update Purpose after archive.
## Requirements
### Requirement: Platform security scanning must not destabilize the K3s control plane
The platform GitOps configuration MUST keep security scanning within a load profile that the repository's single-master K3s-on-LXC control plane can sustain during and after bootstrap.

#### Scenario: Trivy Operator workload scope is explicitly bounded
- **WHEN** the Trivy Operator Application is rendered for this repository
- **THEN** namespace scoping MUST use the supported top-level chart keys
- **AND** the default scope MUST be limited to workload namespaces instead of the whole cluster

#### Scenario: Trivy Operator avoids high-churn scanners by default
- **WHEN** the default platform profile is rendered
- **THEN** Trivy Operator MUST keep vulnerability scanning enabled
- **AND** it MUST disable the higher-churn scanners that are not required for bootstrap correctness on this homelab

#### Scenario: Trivy Operator does not contend with early platform convergence
- **WHEN** the platform Applications are reconciled
- **THEN** Trivy Operator MUST be ordered after the core platform services needed for bootstrap correctness

