# k3s-cni-readiness Specification

## Purpose
TBD - created by archiving change k3s-cni-runtime-idempotence. Update Purpose after archive.
## Requirements
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

### Requirement: GitOps bootstrap waits for cluster nodes to be Ready

The system MUST verify cluster-level node readiness before it starts cluster-side bootstrap components such as Sealed Secrets and ArgoCD.

#### Scenario: Cluster nodes are not fully Ready

- **WHEN** the master does not observe the expected node count or one or more nodes are not `Ready`
- **THEN** the bootstrap MUST stop before GitOps bootstrap and report the current node and kube-system state

#### Scenario: Cluster-side flannel is not ready on every K3s node

- **WHEN** the local node-side flannel gate passes but the master does not observe one Ready cluster-side flannel pod per expected K3s node
- **THEN** the bootstrap MUST stop before GitOps bootstrap and report cluster-side flannel daemonset, pod, and event diagnostics
- **AND** the bootstrap MAY attempt one bounded delete of non-ready flannel pods before failing

#### Scenario: Essential kube-system workloads are not ready before GitOps bootstrap

- **WHEN** cluster-side flannel is present but core `kube-system` deployments required for normal pod startup still do not converge
- **THEN** the bootstrap MUST stop before Sealed Secrets and ArgoCD bootstrap begin
- **AND** the failure output MUST include explicit `kube-system` deployment, pod, and event diagnostics

### Requirement: Healthy CNI readiness preserves the rerun path

The system MUST preserve the normal rerun path when K3s and flannel recover within the expected window.

#### Scenario: Flannel state becomes ready in time

- **WHEN** every node produces local flannel subnet state and all cluster nodes report `Ready` within the configured readiness window
- **THEN** `task up` MUST continue automatically into GitOps bootstrap without manual intervention

