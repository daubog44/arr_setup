## Why

`task up` is still not idempotent even after the K3s/bootstrap fixes, because `tofu apply` tries to update the Proxmox LXC containers in place and strips the extra `idmap` lines that HaaC reconciles later on `/etc/pve/lxc/<vmid>.conf`.

The concrete evidence is:

- `python scripts/haac.py run-tofu --dir tofu plan -no-color` shows three in-place updates whose only planned config deltas are `idmap` removals on the master and both workers
- the active Proxmox provider (`bpg/proxmox` `0.101.1`) does not expose `idmap` in the `proxmox_virtual_environment_container` schema
- the repo intentionally reconciles additional LXC hardware/runtime lines after container creation via `scripts/reconcile_lxc_hardware_block.py` and the related Ansible tasks

That leaves `task up` with a broken contract: a rerun can mutate already-converged containers even when the declared HaaC inputs did not change.

## What Changes

- make the Proxmox LXC resource create-or-replace only, so OpenTofu stops issuing unsafe in-place updates for out-of-band LXC config
- add an explicit declared-container fingerprint that forces replacement when the actual bootstrap spec changes in `.env` or module inputs
- validate the new behavior with a real `tofu plan`, `task -n up`, and a live `task up` rerun when the environment is available

## Impact

- `task up` stops trying to remove HaaC-managed `idmap` lines on converged LXC nodes
- the container bootstrap path becomes rerunnable without reopening the Proxmox drift loop
- intentional container spec changes become explicit replacements instead of silent, unsafe in-place mutations
