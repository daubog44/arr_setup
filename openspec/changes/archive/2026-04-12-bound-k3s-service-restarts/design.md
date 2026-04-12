## Context

Current live evidence shows the rerun path can hang indefinitely inside node configuration:

- `python scripts/haac.py task-run -- up` launched normally from a clean committed tree.
- The run never reached GitOps publication; `haac-stack` stayed `OutOfSync` with the old manifest shape.
- Windows and WSL process inspection showed `ansible-playbook -v` still running after 45 minutes.
- Inside WSL, the long-running worker subprocesses were executing `AnsiballZ_systemd.py` against `192.168.0.212` and `192.168.0.213` while managing `k3s-agent`.

The current playbook uses blocking `ansible.builtin.systemd` tasks and handlers for K3s service restarts. When service recovery is unhealthy, that leaves the operator with a hung rerun instead of a bounded failure.

## Goals / Non-Goals

**Goals:**

- Bound K3s and `k3s-agent` restart/reload waits during `configure-os`.
- Preserve the normal happy path when services recover quickly.
- Emit useful diagnostics on timeout so the next recovery step is obvious.

**Non-Goals:**

- Repair the current cluster's flannel/CNI damage in this change.
- Redesign all service management in the playbook.
- Change the GitOps or workload readiness logic outside the node-configuration phase.

## Decisions

### Use non-blocking service restarts plus explicit bounded wait loops

The current hang is inside service management, not inside a later health probe. The safest first move is to trigger `systemctl restart --no-block` (and `daemon-reload` when needed), then poll `systemctl is-active` in bounded retries instead of letting the Ansible `systemd` module wait indefinitely.

### Capture service status and journal before failing

When the bounded wait expires, the playbook should collect `systemctl status` and recent `journalctl -u <service>` output for the same node. That turns a silent hang into explicit recovery evidence that can be surfaced by `task up`.

### Reuse the same bounded path for both ad hoc restart tasks and handlers

The playbook restarts K3s services from multiple places: GPU runtime reconciliation, fresh worker install, and handlers after service file edits. The fix should cover all of them so rerun behavior is consistent.

## Risks / Trade-offs

- [K3s may legitimately take time to recover] -> Acceptable; the bounded wait can still allow multiple minutes before failure, which is better than an effectively unbounded hang.
- [Status/journal capture adds more playbook steps] -> Acceptable because this path only runs on restart/reload operations and improves operator visibility materially.
- [A non-blocking restart could mark success too early without a follow-up probe] -> Addressed by the explicit `systemctl is-active` polling step.
