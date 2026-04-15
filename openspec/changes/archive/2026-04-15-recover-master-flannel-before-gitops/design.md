## Context

The current playbook already has:

- a bounded node-local flannel recovery task
- a kube-system core readiness gate
- deferred cluster bootstrap installs for Sealed Secrets and ArgoCD

Live evidence still shows a remaining gap: the master can lose `/run/flannel/subnet.env` after the earlier gate but before Sealed Secrets/ArgoCD install timing completes. At that point:

- pods scheduled to the master cannot create sandboxes
- kube-system core on the master drifts to `Unknown`
- Sealed Secrets rollout times out as a secondary effect
- a bounded `k3s` restart can still fail to restore flannel if Longhorn admission is fail-closed with zero endpoints while K3s reapplies control-plane labels during startup

The playbook also applies custom node labels before the networking gate, even though those labels are not needed until later scheduling phases.

## Goals / Non-Goals

**Goals**

- ensure the master enters cluster bootstrap with a fresh, locally valid flannel state
- defer non-essential node mutations until the bootstrap core is stable
- preserve bounded recovery and existing diagnostics

**Non-Goals**

- redesign K3s CNI backend selection
- change workload scheduling policy beyond timing of label application
- add speculative cluster-wide remediation outside the existing bounded recovery path

## Decisions

### Reuse the existing bounded flannel recovery task on the master right before bootstrap installs

The missing contract is local: `/run/flannel/subnet.env` on the master. The playbook should therefore re-check that same contract immediately before Sealed Secrets and ArgoCD installs rather than adding a new speculative recovery path.

### Refresh the degraded Longhorn fail-open workaround immediately before bounded master restart recovery

The live recovery test proved the missing interaction: if Longhorn admission still fails closed with zero endpoints, restarting the master `k3s` service to rebuild flannel can stay stuck in the same degraded state. The bounded flannel recovery path therefore needs a fresh degraded-webhook check immediately before restarting `k3s` on the master.

### Move custom node-label reconciliation after ArgoCD bootstrap

Node labels are not required for Sealed Secrets, ArgoCD namespace creation, or ArgoCD installation. Moving label reconciliation later removes an unnecessary cluster mutation from the fragile bootstrap window.

### Keep the change narrow

The goal is only to close the remaining master-flannel timing gap and remove one non-essential early mutation. Sealed Secrets and ArgoCD logic remain otherwise unchanged.

## Risks / Trade-offs

- If master flannel degradation happens even later than the new pre-bootstrap recheck, this change will not solve it fully.
  - Acceptable. The change is meant to close the currently observed gap with minimal scope.
- Deferring node labels means workload-specific selectors are not present until later in bootstrap.
  - Acceptable because GitOps workload rollout happens after bootstrap and those labels are not required for the Sealed Secrets or ArgoCD controllers themselves.
