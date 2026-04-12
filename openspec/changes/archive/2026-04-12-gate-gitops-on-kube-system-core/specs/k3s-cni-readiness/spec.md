## MODIFIED Requirements

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
