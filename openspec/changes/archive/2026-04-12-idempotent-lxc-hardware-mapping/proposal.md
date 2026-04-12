## Why

`configure-os` currently rewrites the Proxmox LXC hardware/config mapping section in a non-idempotent way:

- it deletes all matching `lxc.idmap`, device, mount, and compatibility lines on every rerun
- it then re-adds the same lines one-by-one
- the resulting task always reports change, which forces `pct stop/start` on every node

That violates the `task-up-idempotence` capability and makes every rerun destabilize K3s, flannel, and later GitOps bootstrap phases even when the desired LXC config has not actually changed.

## What Changes

- Replace the delete-and-readd LXC config pattern with deterministic reconciliation of the HAAC-managed `lxc.*` line set so reruns converge idempotently under Proxmox's own config normalization.
- Keep a safe migration path for legacy unmanaged lines and stale marker remnants so existing or partially migrated nodes are cleaned up without reintroducing perpetual drift.
- Restart an LXC only when the effective HAAC-managed hardware lines actually change.

## Capabilities

### Modified Capabilities

- `task-up-idempotence`

## Impact

- `ansible/playbook.yml`
- live `configure-os` / `task up` rerun behavior
