## Context

The live cluster proved that Falco is not generically impossible on the unprivileged LXC workers. The actual failure is specific to the `modern_ebpf` path: Falco starts, selects the syscall source, then crashes because the ring-buffer map type is not permitted in this environment. The classic `ebpf` probe path is the compatible fallback documented by the Falco chart.

The repo already has a source-of-truth mechanism for runtime node labels through `WORKER_NODES_JSON -> node_labels -> apply_node_labels.yml`, but the current docs still describe the result as unsupported by default. Separately, the Windows operator path copies SSH material into `.tmp/wsl-runtime`, yet the copy step is not idempotent and can fail on rerun.

Finally, recurring work is intentionally split across two execution planes:

- Kubernetes CronJobs for in-cluster recurring workload/control-plane jobs
- Semaphore schedules for infra maintenance that depends on Ansible inventory, jump hosts, and serialized host work

That split is correct, but it is not stated as a stable contract today.

## Goals / Non-Goals

**Goals:**
- Make Falco runtime actually supported on declared compatible unprivileged LXC workers.
- Keep Falco UI and runtime behavior aligned with source-of-truth operator inputs.
- Make WSL runtime SSH material recreation safe across repeated operator runs.
- Document the recurring-job boundary so the current split is intentional and reviewable.

**Non-Goals:**
- Broad auth-surface changes for Headlamp, Semaphore, or other UIs.
- Removing Semaphore-based maintenance.
- Making Falco run on every worker automatically without an explicit compatible-node declaration.

## Decisions

### Use the chart's classic `ebpf` driver for this environment

The live failure is specifically in `modern_ebpf`, not the existence of any syscall probe at all. The official Falco chart already supports `driver.kind: ebpf`, which is the compatible fallback for kernels and runtimes where the modern ring-buffer path is unavailable. This keeps Falco on a supported upstream path instead of introducing a local fork.

Alternative considered:
- Keep `modern_ebpf` and treat runtime detection as unsupported. Rejected because the user requirement is that Falco runtime must function, and the live evidence points to a compatible supported fallback.

### Keep runtime-node selection explicit and source-of-truth driven

Falco runtime will stay bound to explicitly declared workers through repo-managed node labels. That keeps the blast radius small and avoids pretending every unprivileged LXC worker is a valid Falco runtime target. The repo will fail closed when Falco is enabled without any runtime-capable nodes declared.

Alternative considered:
- Schedule Falco on all workers. Rejected because the environment is heterogeneous and the previous failure mode was environment-specific.

### Keep recurring-job ownership split by execution plane

Kubernetes CronJobs remain the right place for recurring in-cluster work such as descheduler, Recyclarr, and K3s DB backups. Semaphore remains the right place for serialized infra maintenance that uses Ansible, jump hosts, maintenance credentials, and host reboot semantics. The change will document this boundary rather than moving jobs just for uniformity.

Alternative considered:
- Move all recurring work into Semaphore or all into CronJobs. Rejected because each plane solves a different trust/runtime problem.

### Make WSL SSH runtime overwrite-safe

The repo-local `.tmp/wsl-runtime` path is the right model, but file materialization must remove or replace existing files before copy. The requirement is idempotent recreation, not a fragile "directory must be absent first" assumption.

## Risks / Trade-offs

- `[Falco runtime still node-specific]` → Keep explicit runtime-node declaration and fail closed when none are declared.
- `[Classic eBPF is less modern than modern_ebpf]` → Prefer the compatible upstream-supported path over a crash-looping path that provides no runtime coverage.
- `[More preflight validation for Falco may block bootstrap]` → Fail early with a clear message instead of silently converging to a UI-only false positive.
- `[WSL cleanup races]` → Remove/copy files atomically enough for the current single-operator workflow and keep runtime cleanup best-effort.

## Migration Plan

1. Update the OpenSpec delta specs for Falco readiness, operator runtime hygiene, and the new maintenance-job boundary.
2. Patch `scripts/haac.py` and `scripts/haaclib/gitops.py` to validate and materialize the runtime inputs safely.
3. Switch the Falco application template to `driver.kind: ebpf`.
4. Re-render the Falco application and values outputs.
5. Validate locally with `helm template`, `kubectl kustomize`, and bootstrap dry-run.
6. Reconcile the live cluster and verify that the Falco daemonset starts on the declared worker and no longer crashes in the old `modern_ebpf` path.

## Open Questions

- None for this change. The live evidence is sufficient to prefer `ebpf` now.
