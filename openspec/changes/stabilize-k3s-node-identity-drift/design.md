## Context

The current bootstrap assumes that the Proxmox LXC inventory declared by OpenTofu is the only active node identity surface. That assumption is false in the live environment:

- OpenTofu state declares the K3s worker VMIDs as `101` and `102`
- Proxmox currently has additional running containers `104` and `105`
- the duplicate containers reuse the same hostnames and IPv4 addresses as `worker2` and `worker1`
- `k3s-agent` enters repeated `duplicate hostname` / node password rejection loops
- worker readiness flaps, which then cascades into `kubectl exec` 502s, Argo repo-server crashes, and Kyverno webhook unavailability

This is not an Argo-level recovery problem. The safe first move is to restore one-to-one node identity before continuing node or workload reconciliation.

## Goals / Non-Goals

**Goals:**
- detect declared K3s LXC identities from repo-managed state
- compare live Proxmox LXCs against that declared set
- identify unmanaged duplicates by hostname or IPv4 collision
- quarantine unmanaged duplicates reversibly with `onboot=0` plus `pct stop`
- invoke the repair automatically before Ansible node configuration

**Non-Goals:**
- deleting orphan LXCs automatically
- reconciling arbitrary Proxmox drift unrelated to declared K3s node identities
- replacing the existing K3s service recovery logic

## Decisions

### Use OpenTofu outputs as the managed identity source

The declared master/worker VMIDs and worker IPs already exist in `tofu output -json` and in the generated inventory. Using OpenTofu outputs keeps the repair path aligned with the repo source of truth instead of scraping ad hoc files.

Alternative considered:
- parse only `ansible/inventory.yml`
  - rejected because VMIDs/IPs are already available as structured OpenTofu output and the inventory is derived from it

### Treat unmanaged duplicates as quarantine candidates, not deletion candidates

The immediate hazard is the duplicate identity, not the mere existence of the container. Disabling `onboot` and stopping the container removes the collision while preserving data for later inspection or manual cleanup.

Alternative considered:
- delete unmanaged duplicate LXCs automatically
  - rejected because that is destructive and harder to justify inside the default rerun path

### Hook the repair before `run-ansible`

The duplicate-node problem blocks node configuration and cascades into later phases. Running the repair right before Ansible makes `task configure-os` and `task up` convergent again without inventing a separate operator ritual.

Alternative considered:
- repair only during `check-env`
  - rejected because the infra may not exist yet and `check-env` intentionally focuses on workstation/input validation

## Risks / Trade-offs

- [False positive on unmanaged LXC] → Match only containers that are outside the declared VMID set and collide on declared hostname or IPv4.
- [Operator surprise from automatic stop] → Emit explicit `[heal]` output naming each quarantined VMID and the collision reason.
- [Managed nodes still need recovery after quarantine] → Follow quarantine with the existing `configure-os` path instead of inventing a second recovery system.
- [State missing or unavailable] → Fail closed and skip quarantine if the declared OpenTofu outputs cannot be read reliably.

## Migration Plan

1. Add helper functions for declared node identity loading, Proxmox LXC inspection, duplicate matching, and quarantine.
2. Add a CLI command so the repair can be invoked directly and from automation.
3. Call the repair path from `cmd_run_ansible` before Ansible begins.
4. Validate live by quarantining unmanaged duplicates, rerunning `configure-os`, and then rerunning GitOps/media verification.

Rollback:
- `pct set <vmid> -onboot 1`
- `pct start <vmid>`

## Open Questions

- None for the first move. Once the cluster is stable again, the orphan LXCs can be handled in a narrower cleanup wave if desired.
