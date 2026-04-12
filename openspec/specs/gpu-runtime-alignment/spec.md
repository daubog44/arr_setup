# gpu-runtime-alignment Specification

## Purpose
TBD - created by archiving change align-nvidia-runtime-with-nfd. Update Purpose after archive.
## Requirements
### Requirement: NFD-selected NVIDIA nodes are runtime-ready
The system MUST not leave the NVIDIA device plugin scheduled onto K3s nodes that lack the runtime prerequisites required to initialize it successfully.

#### Scenario: NFD selects a control-plane or worker node
- **WHEN** the configured NFD-derived NVIDIA hardware labels select a K3s node for the `nvidia-device-plugin` DaemonSet
- **THEN** bootstrap MUST ensure that node's K3s runtime is configured so the plugin can initialize cleanly, or otherwise keep that node out of the placement contract before `haac-stack` is treated as healthy

### Requirement: GPU runtime reconciliation works on rerun
The system MUST keep the NVIDIA device plugin aligned with the nodes that actually expose worker GPU capacity on rerun, without requiring a destructive rebuild.

#### Scenario: Existing control-plane node carries raw NVIDIA labels
- **WHEN** `task up` reruns against a cluster where a control-plane node still carries the raw NFD NVIDIA PCI label but is not intended to serve worker GPU capacity
- **THEN** the reconciled NVIDIA device-plugin placement MUST exclude that control-plane node and allow the worker-scoped device-plugin pods to become healthy as part of the normal rerun flow

