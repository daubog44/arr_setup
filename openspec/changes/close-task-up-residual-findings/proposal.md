## Why

The two residual findings that motivated this change have already been addressed in source, but the active OpenSpec change still describes them as unresolved:

- Falco is already opt-in through `.env`, the rendered [`falco-app.yaml`](C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/k8s/platform/applications/falco-app.yaml) becomes a no-op `List` when `HAAC_ENABLE_FALCO=false`, and `scripts/haac.py` already prunes disabled Falco resources from the cluster.
- `tofu/main.tf` already uses the supported `proxmox_datastores` and `proxmox_download_file` objects, and `task plan` no longer reproduces a provider deprecation warning.

Leaving the change backlog out of sync with the code is now the real issue: the loop can chase phantom work, and the repo docs stop reflecting the actual bootstrap contract.

## What Changes

- Treat Falco's default-disabled LXC path as the accepted steady state for this repo and record that explicitly in the change artifacts.
- Treat the Proxmox provider object migration as already complete and remove the stale spec language that still asks for a rename in `tofu/main.tf`.
- Validate the residual findings against the current source of truth: rendered GitOps output plus real OpenTofu plan output.

## Capabilities

### New Capabilities
- `falco-lxc-readiness`: Falco no longer degrades platform health on this unprivileged LXC K3s platform; it is either explicitly enabled on a supported probe path or cleanly skipped by default.
- `proxmox-datasource-compatibility`: The OpenTofu configuration preserves the supported Proxmox datastore and download-file provider objects and avoids deprecated provider APIs.

### Modified Capabilities

## Impact

- `k8s/platform/applications/falco-app.yaml.template`
- `k8s/platform/applications/falco-app.yaml`
- `tofu/main.tf`
- `task up` platform verification behavior and live cluster health
