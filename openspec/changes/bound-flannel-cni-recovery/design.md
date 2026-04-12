## Context

The current live rerun now fails at the correct boundary:

- `python scripts/haac.py task-run -- configure-os` reaches `K3s Cluster Networking Readiness Gate`
- the helper already performs one bounded `k3s` or `k3s-agent` restart
- affected workers still fail with missing `/run/flannel/subnet.env`
- `journalctl -u k3s-agent` reports repeated pod sandbox failures from the flannel CNI plugin

So the next gap is not another generic K3s restart or another phase-level message. The gap is that the bootstrap does not try one bounded recovery action at the flannel layer before giving up.

## Goals / Non-Goals

**Goals**

- Preserve the current `Node configuration` failure boundary.
- Add one bounded flannel-specific recovery attempt after the existing K3s service recovery path.
- Include cluster-side flannel workload diagnostics in the final failure output.

**Non-Goals**

- Replace flannel or redesign cluster networking.
- Add indefinite retries or a best-effort loop that hides failure.
- Continue into GitOps bootstrap unless flannel readiness actually recovers.

## Decisions

### Recover at the flannel layer after K3s service recovery

The current helper already proves that a plain K3s service restart is not enough. The next recovery move should therefore target the component that owns `subnet.env`, not repeat the same generic restart.

The intended shape is:

- detect the affected node after the initial wait plus bounded service restart still fails
- inspect the cluster-side flannel workload for that node from the master
- perform one bounded flannel-specific recovery action for that node
- re-check `/run/flannel/subnet.env`

### Fail with one combined evidence bundle

If recovery still fails, the operator should get one clear failure payload that includes:

- node-local `systemctl` and `journalctl` output for `k3s` or `k3s-agent`
- node-local routing state
- cluster-side flannel workload status for the affected node

That keeps the rerun path explicit while making the next debugging step obvious.

## Risks / Trade-offs

- The bounded flannel recovery step may still be insufficient.
  - Acceptable. The goal is to try the right layer once and produce stronger evidence, not to promise a full networking self-heal in one change.
- Cluster-side flannel inspection requires master-side Kubernetes access during the helper.
  - Acceptable because the gate already runs only after K3s bootstrap work and before GitOps bootstrap, when the master should be the right place to inspect cluster-side state.
