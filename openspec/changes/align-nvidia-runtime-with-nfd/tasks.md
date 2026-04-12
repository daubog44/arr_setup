## 1. Runtime Alignment

- [x] 1.1 Update `k8s/charts/haac-stack/templates/nvidia-device-plugin.yaml` so NFD-selected NVIDIA placement excludes control-plane nodes that are not intended to expose worker GPU capacity
- [x] 1.2 Keep the worker GPU runtime contract intact and avoid broadening the master K3s runtime path unless new evidence proves it is required

## 2. Validation

- [x] 2.1 Validate the change with `openspec validate align-nvidia-runtime-with-nfd`, focused render/readback checks, and live GPU health evidence (`nvidia-device-plugin` plus node allocatable resources)
- [ ] 2.2 Re-run the live bootstrap path until `wait-for-stack` clears the `haac-stack` GPU blocker or record the exact remaining blocker with the furthest verified phase
