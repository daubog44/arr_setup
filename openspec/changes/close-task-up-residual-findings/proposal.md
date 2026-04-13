## Why

`task up` now succeeds end-to-end, but two residual findings remain after the happy path completes: Falco stays degraded in the `security` namespace on this unprivileged LXC platform, and OpenTofu still emits a deprecated Proxmox datasource warning on every run. Both issues weaken operator confidence because the bootstrap looks successful while leaving platform health and IaC hygiene incomplete.

## What Changes

- Make Falco GitOps rendering capability-gated from `.env` so unsupported unprivileged LXC stacks do not deploy a permanently crash-looping security app by default.
- Keep the enabled Falco deployment explicitly documented as an LXC compatibility choice around the `ebpf` probe path so the repo does not silently depend on host-wide BPF sysctl relaxation.
- Replace the deprecated Proxmox datastore and download-file provider objects with their supported names.
- Validate the result by checking Falco pod health, rerunning `task up`, and confirming the OpenTofu warning disappears.

## Capabilities

### New Capabilities
- `falco-lxc-readiness`: Falco no longer degrades platform health on this unprivileged LXC K3s platform; it is either explicitly enabled on a supported probe path or cleanly skipped by default.
- `proxmox-datasource-compatibility`: The OpenTofu configuration uses the supported Proxmox datastore and download-file provider objects and avoids deprecated provider APIs.

### Modified Capabilities

## Impact

- `k8s/platform/applications/falco-app.yaml.template`
- `k8s/platform/applications/falco-app.yaml`
- `tofu/main.tf`
- `task up` platform verification behavior and live cluster health
