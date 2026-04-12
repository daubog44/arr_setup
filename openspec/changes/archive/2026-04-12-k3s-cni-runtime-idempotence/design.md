## Context

The current live rerun fails like this:

- `task up` reaches `configure-os`
- K3s services report `active`
- `/run/flannel/subnet.env` is still missing on the nodes
- pod sandbox setup fails with `failed to load flannel 'subnet.env' file`
- GitOps bootstrap starts anyway
- the first user-visible failure is the Sealed Secrets controller rollout timeout

The worker GPU runtime path is also still too invasive for reruns:

- worker runtime reconciliation exists in two places
- both runtime tasks are marked changed every time
- one restart path can bounce the control plane even though the runtime work is worker-only
- the fresh-install runtime restart hides failures with `ignore_errors: true`

## Goals / Non-Goals

**Goals**

- Keep K3s runtime reconciliation on GPU workers without forcing it as the cluster-wide default runtime.
- Make reruns restart K3s services only on real drift.
- Fail `task up` on real cluster/CNI unavailability before GitOps bootstrap.
- Align GPU workloads with explicit `runtimeClassName: nvidia`.

**Non-Goals**

- Redesign the whole Kubernetes networking stack.
- Change the LXC privilege model.
- Rework every GPU workload in this change; only the currently tracked GPU consumer needs to be aligned.

## Decisions

### Remove `default-runtime: nvidia` and use explicit workload runtime selection

The repo already wants standard GPU resources plus NFD-based discovery. Keeping `default-runtime: nvidia` makes reruns more disruptive and couples non-GPU pods to GPU runtime state. The safer model is:

- configure the `nvidia` containerd runtime handler on GPU workers
- do not set it as the containerd default
- add a cluster `RuntimeClass` named `nvidia`
- make GPU workloads opt in with `runtimeClassName: nvidia`

### Collapse worker runtime reconciliation to one idempotent path

The duplicated worker runtime steps are the wrong shape for reruns. The playbook should:

- wait for the K3s containerd config to exist
- check whether the `nvidia` runtime handler is already present
- run `nvidia-ctk runtime configure` only when the handler is missing
- restart `k3s-agent` only when config drift or runtime drift actually changed

### Gate GitOps bootstrap on CNI and cluster readiness

`systemctl is-active` is not enough. Before GitOps bootstrap proceeds, the playbook should verify:

- each node has a populated `/run/flannel/subnet.env`
- the master sees the full expected node count
- every node reports `Ready`

When that gate fails, the operator should get explicit K3s/CNI diagnostics, not a later Sealed Secrets timeout.

## Risks / Trade-offs

- [Removing the default runtime could break GPU workloads that relied on implicit runtime selection] -> Addressed by introducing `RuntimeClass nvidia` and opting the tracked GPU workload into it.
- [Flannel readiness may still fail after the runtime/idempotence fix] -> Acceptable; the change then improves failure attribution and preserves the next evidence-backed iteration.
- [A stricter readiness gate can fail earlier than before] -> Intended. Failing on the real K3s/CNI problem is better than surfacing it later as an unrelated GitOps symptom.
