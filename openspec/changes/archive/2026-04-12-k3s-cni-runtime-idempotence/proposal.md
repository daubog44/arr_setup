## Why

`task up` is still failing inside `configure-os`, but the current live failure is no longer the old unbounded K3s restart hang. The rerun reaches GitOps bootstrap with K3s services reported `active` while cluster networking is still broken: `/run/flannel/subnet.env` is missing on the nodes, pod sandbox creation fails with flannel CNI errors, and the first visible symptom becomes the Sealed Secrets rollout timeout.

The worker GPU runtime path also still makes reruns more disruptive than they need to be. The playbook duplicates NVIDIA runtime reconciliation, forces `default-runtime: nvidia`, and restarts `k3s-agent` from always-changing tasks even when no effective runtime drift exists. That violates the operator contract that `task up` is the primary idempotent recovery path.

## What Changes

- Remove the global `default-runtime: nvidia` drift from worker K3s config and stop forcing the NVIDIA runtime as the containerd default.
- Make worker NVIDIA runtime reconciliation idempotent so reruns restart `k3s-agent` only when runtime drift or real K3s config drift exists.
- Add an explicit node/CNI readiness gate before GitOps bootstrap so `task up` fails on the real cluster-readiness problem instead of later surfacing it as a Sealed Secrets timeout.
- Move GPU workloads to an explicit Kubernetes `RuntimeClass` model so GPU runtime selection is per workload instead of cluster-wide.

## Capabilities

### New Capabilities

- `k3s-cni-readiness`: node configuration must verify local flannel/CNI readiness and cluster node readiness before GitOps bootstrap proceeds.

### Modified Capabilities

- `task-up-bootstrap`: `task up` must gate GitOps bootstrap on real K3s/CNI readiness instead of only service-active state.

## Impact

- `ansible/playbook.yml`
- `ansible/tasks/`
- `k8s/charts/haac-stack/templates/`
- `k8s/charts/haac-stack/charts/media/templates/jellyfin.yaml`
- validation and live rerun evidence for `configure-os` / `task up`
