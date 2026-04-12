## ADDED Requirements

### Requirement: K3s node configuration gates on local flannel readiness

The system MUST not proceed from node configuration into GitOps bootstrap until each K3s node has local flannel/CNI state ready for pod sandbox creation.

#### Scenario: Node is missing flannel subnet state

- **WHEN** `configure-os` completes K3s service recovery on a node but `/run/flannel/subnet.env` is still missing or incomplete
- **THEN** the bootstrap MUST fail `Node configuration` before GitOps bootstrap begins
- **AND** the failure output MUST include enough node-local diagnostics to distinguish K3s/CNI readiness problems from later ArgoCD or workload issues

### Requirement: GitOps bootstrap waits for cluster nodes to be Ready

The system MUST verify cluster-level node readiness before it starts cluster-side bootstrap components such as Sealed Secrets and ArgoCD.

#### Scenario: Cluster nodes are not fully Ready

- **WHEN** the master does not observe the expected node count or one or more nodes are not `Ready`
- **THEN** the bootstrap MUST stop before GitOps bootstrap and report the current node and kube-system state

### Requirement: Healthy CNI readiness preserves the rerun path

The system MUST preserve the normal rerun path when K3s and flannel recover within the expected window.

#### Scenario: Flannel state becomes ready in time

- **WHEN** every node produces local flannel subnet state and all cluster nodes report `Ready` within the configured readiness window
- **THEN** `task up` MUST continue automatically into GitOps bootstrap without manual intervention
