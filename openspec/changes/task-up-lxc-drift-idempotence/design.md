## Design

### Problem Shape

The Proxmox provider can create the container, but it cannot fully describe the extra LXC config that HaaC adds later for:

- custom `lxc.idmap`
- GPU passthrough device and mount lines
- TUN and eBPF compatibility mounts

Because those lines are outside the provider schema, every future in-place update is unsafe: the provider refreshes remote state, notices lines it does not own, and then rewrites the container config back toward its narrower model.

### Chosen Model

Treat the LXC resource as:

- declarative at creation time
- drift-tolerant at steady state
- replacement-based when the declared bootstrap spec changes

That means:

1. the container resource ignores in-place drift after creation
2. a separate `terraform_data` fingerprint tracks the declared container bootstrap spec
3. when the declared spec changes, the container is replaced instead of updated in place

### Why This Model

- it matches the real provider capability today
- it preserves `.env` as the source of truth
- it keeps `task up` idempotent on converged clusters
- it avoids pretending that OpenTofu can safely own fields that are actually reconciled by later host-side automation

### Tradeoff

Intentional spec changes to the base LXC declaration become destructive replacements, not in-place updates. That is acceptable here because unsafe in-place mutations are worse: they silently strip required runtime config and destabilize the cluster.

### Validation

- `tofu plan` should become a no-op for the converged cluster
- `python scripts/haac.py task-run -- -n up` should still pass
- `task up` should move beyond `provision-infra` without reintroducing the old LXC drift
