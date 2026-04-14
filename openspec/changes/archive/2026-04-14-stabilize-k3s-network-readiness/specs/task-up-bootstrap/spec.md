## MODIFIED Requirements

### Requirement: `configure-os` uses evidence-backed K3s networking readiness gates

The bootstrap path MUST gate GitOps bootstrap on K3s networking conditions that are actually observed on this cluster.

#### Scenario: local flannel state is missing on a node

- **WHEN** `/run/flannel/subnet.env` is missing or unusable on a K3s server or agent
- **THEN** the playbook performs at most one bounded local restart of the relevant `k3s` service
- **AND** if the file is still missing afterwards, the playbook fails with captured diagnostics instead of attempting speculative cluster-side flannel pod recovery

#### Scenario: degraded Longhorn admission webhooks are blocking bootstrap recovery

- **WHEN** the Longhorn admission service exists but has zero endpoints during bootstrap recovery
- **AND** either Longhorn admission webhook is still configured with `failurePolicy: Fail`
- **THEN** the playbook temporarily relaxes that webhook to `Ignore` before bootstrap node mutations and flannel recovery continue
- **AND** the playbook performs one coordinated K3s agent-then-server restart sequence before checking local flannel state again
- **AND** the playbook does not apply this workaround on fresh clusters where Longhorn is absent or already healthy

#### Scenario: cluster-side pre-GitOps gate runs after node readiness

- **WHEN** all expected Kubernetes nodes report `Ready`
- **THEN** the cluster-wide pre-GitOps gate validates only essential kube-system workload readiness and not a flannel daemonset or pod contract that is not guaranteed by this cluster
