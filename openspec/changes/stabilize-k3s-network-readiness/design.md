## Context

The bootstrap flow already has node readiness checks and a dedicated wait for `/run/flannel/subnet.env` on each node. That local file is the observed K3s networking contract that determines whether the node is ready for GitOps bootstrap.

However, a separate post-node gate still tries to reason about cluster-side flannel pods and daemonsets. Live evidence on this cluster showed:

- no flannel pod was found on the affected master
- deleting or waiting on cluster-side flannel pods is not a safe or valid recovery path here
- a previous Longhorn install can leave `validator.longhorn.io` and `longhorn-webhook-mutator` in `failurePolicy: Fail` while the admission service has zero endpoints
- once that happens, K3s server-side node mutations and bootstrap node labeling can fail closed even though the intended recovery is network-focused

## Goals / Non-Goals

**Goals**

- keep the node-local flannel gate as the authoritative networking readiness contract
- make the post-node gate validate only cluster-wide conditions that are actually required for GitOps bootstrap
- prevent degraded Longhorn admission webhooks from blocking bootstrap recovery when Longhorn itself is not serving endpoints
- produce actionable diagnostics on failure

**Non-Goals**

- redesign the K3s CNI choice
- change the Sealed Secrets install flow itself
- introduce speculative remediation for unknown master-side slowness without evidence

## Decisions

### Treat `/run/flannel/subnet.env` as the node-side readiness contract

This file is the clearest observed signal that the local K3s service has rebuilt its networking state. Recovery should therefore stay local to the affected node and be bounded.

### Remove cluster-side flannel pod expectations from the pre-GitOps gate

The cluster-wide gate should validate node readiness and essential kube-system workloads only. It should not assume a visible flannel daemonset or pod model unless the cluster demonstrably uses one.

### Preserve diagnostics, not speculative recovery

When networking still fails after one bounded local service recovery, the playbook should capture journals, routes, node state, kube-system pods, and events, then fail explicitly.

### Fail open only when Longhorn admission is provably degraded

The playbook should only relax Longhorn admission webhook `failurePolicy` when all of the following are true:

- the Longhorn admission service exists
- the service currently has zero endpoints
- the relevant webhook is still set to `Fail`

That keeps the workaround targeted to rerun recovery, avoids changing fresh clusters that do not have Longhorn yet, and matches the manually verified recovery path that brought `/run/flannel/subnet.env` back on every node.

### Bounce workers before the server after the degraded-webhook workaround

Manual recovery proved that simply relaxing the webhook was not sufficient; the cluster only rebuilt `/run/flannel/subnet.env` after restarting the workers and then the server in that degraded state. The playbook should mirror that sequence once, and only when the degraded-webhook workaround was actually applied.

## Risks / Trade-offs

- If a future cluster version does expose flannel pods again, this change will not use them for recovery.
  - Acceptable. Diagnostics remain sufficient, and speculative pod deletion is riskier than bounded local recovery.
- This change does not guarantee full `task up` success by itself.
  - Acceptable. Its scope is to make the K3s networking gate correct and observable.
- Temporarily switching degraded Longhorn admission webhooks to `Ignore` reduces protection while Longhorn is down.
  - Acceptable for bootstrap recovery. The change is scoped to the broken rerun case where the cluster is already unable to self-heal, and later reconciliation can restore the intended policy.
