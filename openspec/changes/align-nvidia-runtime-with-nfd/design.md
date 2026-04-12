## Context

Live evidence shows a narrow but blocking mismatch:

- `python scripts/haac.py task-run -- up` now reaches `wait-for-stack`, then stops because ArgoCD reports `haac-stack` degraded while waiting for `apps/DaemonSet/nvidia-device-plugin`.
- The `kube-system` DaemonSet is healthy on `haacarr-worker1` and `haacarr-worker2`, but the master pod crash-loops with the upstream NVIDIA message that the node either lacks runtime prerequisites or should not have been selected.
- All nodes carry `feature.node.kubernetes.io/pci-0300_10de.present=true`, but only the two workers currently expose allocatable `nvidia.com/gpu`.
- `ansible/playbook.yml` currently keeps the NVIDIA runtime path on workers, which matches the live node state where only workers expose allocatable `nvidia.com/gpu`.

This is not a generic Helm failure. It is a contract gap between node bootstrap and the existing NFD-based GPU placement model.

## Goals / Non-Goals

**Goals:**

- Ensure the NVIDIA device-plugin only targets nodes that are intended to serve GPU workloads in the current cluster model.
- Keep GPU placement centered on NFD-derived discovery rather than reviving legacy custom scheduling labels.
- Make rerun reconciliation fix an existing master node without requiring cluster recreation.

**Non-Goals:**

- Redesign GPU workload scheduling beyond the current NVIDIA device-plugin contract.
- Introduce a full custom GPU capability inventory system when the current gap can be fixed by aligning existing bootstrap behavior.
- Change Intel GPU handling unless the NVIDIA fix reveals the same structural issue there.

## Decisions

### Keep the worker GPU runtime path and tighten placement on the control plane

The live cluster already exposes `nvidia.com/gpu` only on the two workers. That makes control-plane exclusion the safer first move: the chart should continue to use NFD-derived NVIDIA labels, but each nodeSelector term should also reject `node-role.kubernetes.io/control-plane`.

### Prefer a standard role exclusion over new custom GPU labels

Adding bespoke labels would work, but it would reintroduce the repo-local GPU labeling pattern the architecture deliberately moved away from. A control-plane exclusion keeps the source of hardware truth in NFD while using a standard Kubernetes node-role label to avoid scheduling the plugin onto the master.

### Leave Ansible untouched unless worker runtime evidence changes

Current live evidence does not show missing `nvidia.com/gpu` capacity on the workers. Unless a later validation proves that the worker runtime path itself is incomplete, the change should stay in the Helm placement layer instead of broadening the K3s server runtime surface.

## Risks / Trade-offs

- [A control-plane exclusion is narrower than a full per-node runtime discovery model] -> Acceptable for the first move because the current live cluster already exposes GPU capacity only on workers and the blocker is specifically the master DaemonSet pod.
- [Future GPU-enabled control-plane nodes would need a different policy] -> Re-evaluate only if the homelab intentionally starts scheduling GPU workloads on control-plane nodes.
- [The live cluster is already degraded from interrupted recovery attempts] -> Treat the cluster CNI state as a separate validation blocker if it prevents a clean rerun after the placement patch is in place.
