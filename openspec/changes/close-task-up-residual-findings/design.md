## Overview

This change closes two independent residual findings that remain after the bootstrap path already succeeds:

1. Falco's `modern_ebpf` driver crashes inside the unprivileged Proxmox LXC nodes because the guest kernel environment exposes `kernel.unprivileged_bpf_disabled=2` and `kernel.perf_event_paranoid=4`, which is incompatible with the modern ring-buffer probe path seen in the live Falco logs. The fallback `ebpf` probe path still cannot be built reliably on these guests because there is no prebuilt probe for the running `6.17.2-1-pve` kernel, the loader cannot fetch matching headers, and the nested container cannot mount `debugfs`.
2. The Proxmox provider warns that `proxmox_virtual_environment_datastores` is deprecated and should be replaced by `proxmox_datastores`.

## Decisions

### 1. Make Falco opt-in on this LXC environment and keep the enabled path on `ebpf`

The live Falco logs show:

- `Opening 'syscall' source with modern BPF probe`
- `libpman: ring buffer map type is not supported (errno: 1 | message: Operation not permitted)`

This is not a generic Falco misconfiguration. It is an environment mismatch between the modern probe and the nested unprivileged LXC kernel policy. Lowering the host-wide BPF and perf sysctls on Proxmox would be a broader security tradeoff than this bootstrap should make implicitly.

The safer fix is:

- disable Falco by default in `.env` on this unprivileged LXC stack
- render a no-op GitOps manifest when disabled so platform health stays clean
- keep the enabled manifest on the classic `ebpf` path, documented as an explicit opt-in that requires matching kernel probe prerequisites

That avoids a permanently degraded security namespace without introducing a host-global security downgrade or pretending the probe path is supported when it is not.

### 2. Rename the Proxmox datastore datasource

The provider schema currently exposes both:

- `proxmox_virtual_environment_datastores` as deprecated
- `proxmox_datastores` as the supported replacement

The attribute shape is equivalent for this repo's usage, so the change is a direct rename in `tofu/main.tf`.

## Verification

- `helm template` must still render the Falco application values cleanly.
- A live GitOps reconciliation must remove Falco crash loops from platform health. On this default stack that means the Falco application is absent after reconciliation; on an explicitly supported opt-in stack it means the DaemonSet becomes `Ready`.
- `task up` must still succeed end-to-end.
- OpenTofu apply output must no longer print the deprecated datastore datasource warning.
