## Context

The live cluster proved that Falco is not generically impossible on the unprivileged LXC workers. The initial diagnosis was incomplete: the first `modern_ebpf` failure happened before the workers exposed the required host kernel metadata. After adding the kernel metadata mounts, the legacy `ebpf` fallback turned out to be the wrong model because it forces in-guest probe compilation against a host toolchain and glibc version the Debian 12 guest does not have. The compatible upstream path for this environment is `modern_ebpf` with explicit host and LXC prerequisites.

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

### Use the chart's `modern_ebpf` driver with explicit host prerequisites

The official Falco chart already supports `driver.kind: modern_ebpf`, which avoids the in-guest probe compilation path entirely. In this environment, once the runtime-capable workers expose `/usr/lib/modules`, `/usr/src`, and `/sys/kernel/*`, the `modern_ebpf` path is the correct supported upstream path because it no longer depends on the Debian 12 guest having the same glibc and compiler toolchain as the Proxmox host kernel build.

Alternative considered:
- Keep `modern_ebpf` without adding host prerequisites. Rejected because the live evidence now shows the kernel metadata exposure is required for the Falco runtime to initialize correctly on this LXC model.

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
- `[modern_ebpf still depends on node prerequisites]` → Keep explicit runtime-node declaration and mount the kernel metadata only on those declared workers.
- `[More preflight validation for Falco may block bootstrap]` → Fail early with a clear message instead of silently converging to a UI-only false positive.
- `[WSL cleanup races]` → Remove/copy files atomically enough for the current single-operator workflow and keep runtime cleanup best-effort.

## Migration Plan

1. Update the OpenSpec delta specs for Falco readiness, operator runtime hygiene, and the new maintenance-job boundary.
2. Patch `scripts/haac.py` and `scripts/haaclib/gitops.py` to validate and materialize the runtime inputs safely.
3. Switch the Falco application template back to `driver.kind: modern_ebpf` and add the required host kernel metadata mounts.
4. Re-render the Falco application and values outputs.
5. Validate locally with `helm template`, `kubectl kustomize`, and bootstrap dry-run.
6. Reconcile the live cluster and verify that the Falco daemonset starts on the declared worker without falling back to legacy in-guest probe compilation.

## Open Questions

- None for this change. The live evidence is sufficient to prefer `modern_ebpf` once the host prerequisites are in place.
