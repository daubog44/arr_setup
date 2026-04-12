## Context

The current LXC hardware mapping tasks generate the correct desired lines, but they reconcile them destructively:

- delete legacy matching lines from `/etc/pve/lxc/<vmid>.conf`
- add the desired lines back one-by-one
- restart the container whenever the add step reports change

Because the delete step runs on every invocation, the add step also changes on every invocation. That makes `configure-os` non-convergent.

## Goals / Non-Goals

**Goals**

- Make the LXC hardware mapping section converge without change when desired config is already present.
- Preserve compatibility with existing nodes that still have the old unmanaged line set.
- Keep restart behavior strict: only restart a node when effective LXC config drift exists.

**Non-Goals**

- Redesign the GPU/TUN/eBPF mapping model itself.
- Change the unprivileged LXC baseline.
- Remove the NAS bind or other currently intended mounts.

## Decisions

### Reconcile the canonical HAAC-managed `lxc.*` line set directly

The desired `lxc.idmap`, device, mount, and compatibility lines are already rendered deterministically. The reconciler should therefore compare that exact ordered line set with the current Proxmox config and rewrite it only when drift exists.

This gives:

- deterministic ordering
- idempotent reruns
- strict restart behavior tied to real config drift

### Strip legacy duplicates and stale markers during reconciliation

Older runs wrote the same lines without markers, and an interrupted migration can leave stale `# BEGIN/# END HAAC MANAGED LXC HARDWARE` comments behind. Live Proxmox runs also normalize recognized `lxc.*` lines after `pct start`, which means comment markers are not a stable ownership boundary for these lines.

The reconciliation step therefore needs to remove:

- all currently managed `lxc.*` lines that belong to HAAC
- any stale marker comments from earlier migration attempts

and then reinsert the desired managed lines in canonical order at the existing managed-line location, or at EOF when the config has none yet.

The migration rule is:

- if the current managed line set already matches the desired ordered lines, do nothing
- otherwise remove the old managed lines and stale markers, then write the desired managed lines back once
- on later runs, do nothing unless the actual managed line set differs again

That keeps the migration safe while also recovering from partial first-run states without depending on markers that Proxmox later reflows away from the managed lines.

## Risks / Trade-offs

- The first rerun after this change still restarts the LXCs once.
  - Acceptable. That is the migration step.
- The final persisted config no longer carries HAAC marker comments.
  - Acceptable because live Proxmox normalization does not preserve a stable marker-wrapped block for these lines; convergence matters more than comment grouping.
