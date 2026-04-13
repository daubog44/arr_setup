## Why

`task up` now succeeds end-to-end, but two residual findings remain after the happy path completes: Falco stays degraded in the `security` namespace, and OpenTofu still emits a deprecated Proxmox datasource warning on every run. Both issues weaken operator confidence because the bootstrap looks successful while leaving platform health and IaC hygiene incomplete.

## What Changes

- Switch the Falco chart values used by the platform GitOps app from `modern_ebpf` to the supported `ebpf` probe path for this unprivileged LXC-based K3s environment.
- Keep the Falco deployment explicitly documented as an LXC compatibility choice so the repo does not silently depend on host-wide BPF sysctl relaxation.
- Replace the deprecated Proxmox datastore and download-file provider objects with their supported names.
- Validate the result by checking Falco pod health, rerunning `task up`, and confirming the OpenTofu warning disappears.

## Capabilities

### New Capabilities
- `falco-lxc-readiness`: Falco converges on this unprivileged LXC K3s platform without requiring host-wide weakening of Proxmox BPF restrictions.
- `proxmox-datasource-compatibility`: The OpenTofu configuration uses the supported Proxmox datastore and download-file provider objects and avoids deprecated provider APIs.

### Modified Capabilities

## Impact

- `k8s/platform/applications/falco-app.yaml.template`
- `k8s/platform/applications/falco-app.yaml`
- `tofu/main.tf`
- `task up` platform verification behavior and live cluster health
