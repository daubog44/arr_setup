## Why

`k3s-cni-runtime-idempotence` proved the new readiness gate is doing the right thing: after the helper-var fix, a real `python scripts/haac.py task-run -- configure-os` rerun now stops in `Node configuration` instead of drifting into a later GitOps timeout. The remaining blocker is narrower and concrete:

- worker nodes still do not produce `/run/flannel/subnet.env` even after one bounded `k3s-agent` restart
- the captured `journalctl -u k3s-agent` output shows repeated `CreatePodSandboxError` entries caused by `plugin type="flannel" failed (add): failed to load flannel 'subnet.env' file`

That means the missing capability is no longer phase attribution. It is bounded flannel-specific recovery. `task up` still lacks an automated first recovery move for this failure mode, so reruns stop on the same symptom without attempting the flannel layer that actually owns `subnet.env`.

## What Changes

- Extend the flannel readiness helper to capture cluster-side flannel workload state from the master for the failing node.
- Attempt one bounded flannel-specific recovery action after the existing K3s service restart path.
- Fail with combined node-local and cluster-side flannel diagnostics if the node still does not recover.

## Capabilities

### Modified Capabilities

- `k3s-cni-readiness`

## Impact

- `ansible/playbook.yml`
- `ansible/tasks/wait_for_flannel_subnet_env.yml`
- live `configure-os` / `task up` validation evidence
