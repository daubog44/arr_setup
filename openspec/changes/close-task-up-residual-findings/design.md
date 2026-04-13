## Overview

This change closes two independent residual findings that remain after the bootstrap path already succeeds:

1. Falco's `modern_ebpf` driver crashes inside the unprivileged Proxmox LXC nodes because the guest kernel environment exposes `kernel.unprivileged_bpf_disabled=2` and `kernel.perf_event_paranoid=4`, which is incompatible with the modern ring-buffer probe path seen in the live Falco logs. The fallback `ebpf` probe path still cannot be built reliably on these guests because there is no prebuilt probe for the running `6.17.2-1-pve` kernel, the loader cannot fetch matching headers, and the nested container cannot mount `debugfs`.
2. The change artifacts still describe a deprecated Proxmox provider rename, but the repository already uses the supported `proxmox_datastores` and `proxmox_download_file` object names and current `task plan` output no longer reproduces that warning.

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

### 2. Preserve the supported Proxmox provider objects and remove stale rename work

The repository already has the supported provider object names in [`tofu/main.tf`](C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/tofu/main.tf):

- `proxmox_datastores`
- `proxmox_download_file`

`scripts/haac.py` also already handles the legacy download-file state address migration before plan/apply. The real work is therefore not another code rename. It is to align the active OpenSpec artifacts with the code and with the current `task plan` evidence so the loop does not keep trying to rewrite an already-correct file.

## Verification

- `helm template` must still render the Falco application values cleanly.
- A live GitOps reconciliation must remove Falco crash loops from platform health. On this default stack that means the Falco application is absent after reconciliation; on an explicitly supported opt-in stack it means the DaemonSet becomes `Ready`.
- `task up` must still succeed end-to-end when the environment is available.
- `task plan` and the current OpenTofu plan/apply path must not print the deprecated datastore datasource warning.
