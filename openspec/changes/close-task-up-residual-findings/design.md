## Overview

This change closes two independent residual findings that remain after the bootstrap path already succeeds:

1. Falco's `modern_ebpf` driver crashes inside the unprivileged Proxmox LXC nodes because the guest kernel environment exposes `kernel.unprivileged_bpf_disabled=2` and `kernel.perf_event_paranoid=4`, which is incompatible with the modern ring-buffer probe path seen in the live Falco logs.
2. The Proxmox provider warns that `proxmox_virtual_environment_datastores` is deprecated and should be replaced by `proxmox_datastores`.

## Decisions

### 1. Use Falco's legacy `ebpf` probe path for this LXC environment

The live Falco logs show:

- `Opening 'syscall' source with modern BPF probe`
- `libpman: ring buffer map type is not supported (errno: 1 | message: Operation not permitted)`

This is not a generic Falco misconfiguration. It is an environment mismatch between the modern probe and the nested unprivileged LXC kernel policy. Lowering the host-wide BPF and perf sysctls on Proxmox would be a broader security tradeoff than this bootstrap should make implicitly.

The safer fix is:

- keep Falco enabled
- keep it privileged inside the pod as before
- switch the driver from `modern_ebpf` to `ebpf`

That preserves syscall-based Falco coverage without introducing a host-global security downgrade.

### 2. Rename the Proxmox datastore datasource

The provider schema currently exposes both:

- `proxmox_virtual_environment_datastores` as deprecated
- `proxmox_datastores` as the supported replacement

The attribute shape is equivalent for this repo's usage, so the change is a direct rename in `tofu/main.tf`.

## Verification

- `helm template` must still render the Falco application values cleanly.
- A live GitOps reconciliation must move the Falco DaemonSet to `Ready`.
- `task up` must still succeed end-to-end.
- OpenTofu apply output must no longer print the deprecated datastore datasource warning.
