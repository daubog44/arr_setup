## Context

The live cluster disproved the original model of running the Falco runtime sensor as an in-cluster DaemonSet inside unprivileged Proxmox LXC workers. The initial `modern_ebpf` failure was partly caused by missing kernel metadata mounts, but after fixing those mounts the runtime still failed on BPF ring-buffer setup with `Operation not permitted`. That means the remaining blocker is the unprivileged LXC capability boundary itself, not only guest toolchain drift.

The compatible upstream path for this repo is:

- install the Falco sensor on the Proxmox host with `modern_ebpf`
- forward Falco events through `http_output`
- keep `falcosidekick` and its protected UI in-cluster as the single alert ingest and operator surface

The repo already has a source-of-truth ingress catalog that drives Homepage, HTTPRoutes, and public URL verification. Falco should integrate with that same catalog through the cluster-side UI service. Separately, the Windows operator path copies SSH material into `.tmp/wsl-runtime`, and that copy step must stay overwrite-safe on rerun.

Finally, recurring work is intentionally split across two execution planes:

- Kubernetes CronJobs for in-cluster recurring workload/control-plane jobs
- Semaphore schedules for infra maintenance that depends on Ansible inventory, jump hosts, and serialized host work

That split is correct, but it must stay documented as a stable contract.

## Goals / Non-Goals

**Goals:**
- Make Falco runtime actually supported in this repo through a dedicated host-side sensor path.
- Keep Falco UI and runtime behavior aligned with source-of-truth operator inputs and the public ingress catalog.
- Make WSL runtime SSH material recreation safe across repeated operator runs.
- Document the recurring-job boundary so the current split is intentional and reviewable.

**Non-Goals:**
- Broad auth-surface changes for Headlamp, Semaphore, or other UIs.
- Removing Semaphore-based maintenance.
- Making Falco run as an in-cluster sensor on every worker automatically.

## Decisions

### Split Falco into a host-side sensor plus cluster-side Falcosidekick

The platform-side application should no longer deploy the upstream `falco` chart. Instead, it should deploy the upstream `falcosidekick` chart only, with:

- the core receiver service exposed internally in-cluster
- the UI published through the existing edge-auth route
- a dedicated repo-managed `NodePort` ingest service that gives the Proxmox host a stable HTTP target

Alternative considered:
- Keep trying to run the sensor in unprivileged LXC guests. Rejected because the remaining BPF ring-buffer failure is a capability boundary, not only a configuration gap.

### Install the actual Falco sensor on the Proxmox host with `modern_ebpf`

The Proxmox host is the supported sensor surface in this repo because it is not constrained by the unprivileged LXC BPF capability boundary. The playbook should:

- install the official Falco package on Proxmox
- configure `modern_ebpf`
- write a dedicated drop-in under `/etc/falco/config.d/`
- enable JSON output and `http_output`
- forward events to the cluster-side ingest endpoint on the K3s master IP and a fixed node port

Alternative considered:
- Push Falco alerts directly from the host to an external SaaS endpoint. Rejected because the repo already owns a cluster-side security surface and notification fan-out through Falcosidekick.

### Remove runtime-worker fail-closed validation for Falco

Once the sensor leaves the worker DaemonSet model, Falco enablement no longer depends on `haac.io/falco-runtime` labels in `WORKER_NODES_JSON`. Those labels can remain for future experiments, but the bootstrap path must not require them.

### Keep recurring-job ownership split by execution plane

Kubernetes CronJobs remain the right place for recurring in-cluster work such as descheduler, Recyclarr, and K3s DB backups. Semaphore remains the right place for serialized infra maintenance that uses Ansible inventory, jump hosts, maintenance credentials, and host reboot semantics. The change will document this boundary rather than moving jobs just for uniformity.

### Keep WSL SSH runtime overwrite-safe

The repo-local `.tmp/wsl-runtime` path remains the right model, but file materialization must always replace any prior runtime copy before the current run starts.

## Risks / Trade-offs

- `[Falco host sensor sees host syscalls, not guest-only namespaces]` -> Accept this because the requirement is supported runtime coverage in this environment, and the previous guest-sensor path is not supportable.
- `[NodePort couples Falco ingest to the current K3s master IP]` -> Derive the host target from the same source-of-truth inventory used by the rest of the bootstrap and keep the node port fixed and explicit.
- `[More preflight validation for Falco may block bootstrap]` -> Fail early with a clear message instead of silently converging to a UI-only false positive.
- `[WSL cleanup races]` -> Remove/copy files atomically enough for the current single-operator workflow and keep runtime cleanup best-effort.

## Migration Plan

1. Update the OpenSpec delta specs for Falco readiness, operator runtime hygiene, and the new maintenance-job boundary.
2. Patch `scripts/haac.py` and `scripts/haaclib/gitops.py` to validate and materialize the runtime inputs safely.
3. Replace the platform Falco application template with the `falcosidekick` chart and add a repo-managed ingest `NodePort` service.
4. Add Proxmox-host Falco package installation and configuration through `ansible/playbook.yml`.
5. Re-render the Falco application and platform outputs.
6. Validate locally with `helm template`, `kubectl kustomize`, and bootstrap dry-run.
7. Reconcile the live cluster and verify that:
   - Falcosidekick UI stays reachable through the existing public route
   - the Proxmox host Falco service is active
   - the host Falco config points at the cluster ingest endpoint
   - recurring job ownership remains documented and unchanged

## Open Questions

- None for this change. The live evidence is sufficient to prefer a host-side `modern_ebpf` sensor over the previous in-cluster unprivileged LXC model.
