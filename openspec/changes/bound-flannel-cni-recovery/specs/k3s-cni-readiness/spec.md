## MODIFIED Requirements

### Requirement: K3s node configuration gates on local flannel readiness

The system MUST not proceed from node configuration into GitOps bootstrap until each K3s node has local flannel/CNI state ready for pod sandbox creation.

#### Scenario: Node is missing flannel subnet state

- **WHEN** `configure-os` completes K3s service recovery on a node but `/run/flannel/subnet.env` is still missing or incomplete
- **THEN** the bootstrap MUST fail `Node configuration` before GitOps bootstrap begins
- **AND** the failure output MUST include enough node-local diagnostics to distinguish K3s/CNI readiness problems from later ArgoCD or workload issues

#### Scenario: Missing flannel subnet state triggers bounded flannel recovery

- **WHEN** a node still lacks a usable `/run/flannel/subnet.env` after the bounded K3s service recovery path
- **THEN** the bootstrap MUST inspect the cluster-side flannel workload for the affected node and perform one bounded flannel-specific recovery action before failing
- **AND** if the node still does not recover, the failure output MUST include both node-local K3s diagnostics and cluster-side flannel workload status

#### Scenario: Flannel-specific recovery restores readiness

- **WHEN** the bounded flannel-specific recovery action restores `/run/flannel/subnet.env` and the affected node becomes healthy within the configured window
- **THEN** `task up` MUST continue automatically without manual intervention
