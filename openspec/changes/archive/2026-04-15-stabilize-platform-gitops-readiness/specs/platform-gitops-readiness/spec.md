## ADDED Requirements

### Requirement: platform GitOps readiness must converge past ArgoCD self-management

The `task up` GitOps readiness phase MUST NOT stop at `haac-platform` because the ArgoCD self-management Application references an invalid or unpublished install overlay.

#### Scenario: ArgoCD self-management syncs during bootstrap

- **WHEN** `task up` reaches the `haac-platform` readiness gate
- **THEN** the `argocd` child Application sync source is available in the GitOps repo
- **AND** the self-managed overlay can render without a remote manifest fetch at reconcile time
- **AND** the repo-server customization renders as a valid merged Deployment
- **AND** `haac-platform` can become `Synced` and `Healthy` instead of remaining `OutOfSync`

### Requirement: monitoring-dependent platform apps must tolerate bootstrap CRD ordering

Platform Applications that render `ServiceMonitor` MUST NOT fail first bootstrap sync solely because the monitoring CRDs are landing in an earlier platform wave.

#### Scenario: monitoring CRDs are not present at the first dependent app sync attempt

- **WHEN** `node-problem-detector` or `trivy-operator` sync before `ServiceMonitor` is fully established
- **THEN** the bootstrap path tolerates the transient missing resource validation
- **AND** those Applications are ordered after `kube-prometheus-stack`
- **AND** the platform readiness gate can converge once the CRDs exist
