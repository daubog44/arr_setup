## Why

The second live `task up` rerun now reaches the `haac-stack` workload gate, but ArgoCD keeps the application degraded because `nvidia-device-plugin` lands on `haacarr-master` and crash-loops there. Node Feature Discovery currently marks all three K3s nodes with the raw NVIDIA PCI label, but only the two workers actually expose allocatable `nvidia.com/gpu`. The safer first fix is to keep the control-plane node out of the NVIDIA device-plugin placement contract while retaining the existing worker GPU runtime path.

## What Changes

- Align the NVIDIA device-plugin placement contract with the nodes that actually expose worker GPU capacity by excluding control-plane nodes even when they carry raw NVIDIA PCI labels.
- Keep GPU scheduling centered on NFD-derived discovery instead of reintroducing legacy custom GPU labels, but tighten placement so raw hardware labels on the control plane do not leave `haac-stack` degraded.
- Add validation that checks both the `nvidia-device-plugin` health and node-level `nvidia.com/gpu` allocation before treating the workload application gate as converged.

## Capabilities

### New Capabilities
- `gpu-runtime-alignment`: define how K3s runtime configuration and NFD-based NVIDIA device-plugin placement stay aligned across master and worker nodes.

### Modified Capabilities

## Impact

- `k8s/charts/haac-stack/templates/nvidia-device-plugin.yaml`
- `ansible/playbook.yml` only if later evidence proves the worker GPU runtime path itself is incomplete
- validation and worklog evidence around live GPU readiness and `haac-stack`
