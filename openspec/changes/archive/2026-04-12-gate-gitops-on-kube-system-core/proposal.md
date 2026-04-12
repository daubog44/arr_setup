## Why

`bound-flannel-cni-recovery` improved the local node-side flannel gate and proved a narrower remaining blind spot during the next live `python scripts/haac.py task-run -- configure-os` rerun:

- `haacarr-worker2` still failed in `Node configuration`
- the new master-side diagnostics reported no flannel pod and no flannel daemonset summary for that node before or after the bounded flannel recovery attempt
- the bootstrap still only had a node `Ready` gate before it moved toward Sealed Secrets and later GitOps bootstrap phases

That means `task up` still lacks one important capability: it can treat the cluster as ready for GitOps bootstrap even when the cluster-side flannel workload and other core `kube-system` components are not healthy enough to start normal pods.

## What Changes

- Gate GitOps bootstrap on cluster-side flannel readiness across every K3s node.
- Gate GitOps bootstrap on essential `kube-system` deployments that prove the cluster can start core pods before Sealed Secrets is installed.
- If Sealed Secrets still fails after that stronger gate, emit controller-specific deployment, pod, log, and event diagnostics instead of a generic rollout timeout.

## Capabilities

### Modified Capabilities

- `k3s-cni-readiness`
- `task-up-bootstrap`

## Impact

- `ansible/playbook.yml`
- `ansible/tasks/wait_for_kube_system_core.yml`
- live `configure-os` / `task up` validation evidence
