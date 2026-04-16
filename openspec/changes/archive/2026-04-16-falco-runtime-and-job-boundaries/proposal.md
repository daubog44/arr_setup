## Why

Falco is currently published as a healthy UI while the active change still models runtime coverage as an in-cluster DaemonSet on unprivileged Proxmox LXC workers. Live evidence disproved that model: even after the required kernel metadata mounts were added, the `modern_ebpf` path still fails inside the unprivileged guests with `Operation not permitted` on BPF ring buffer setup. The supported runtime path for this repo needs to move to a dedicated host-side Falco sensor on Proxmox, with cluster-side Falcosidekick providing the alert ingest and protected UI.

At the same time, the Windows WSL bridge still needs to keep its SSH runtime path idempotent on rerun, and the split between in-cluster CronJobs and Semaphore maintenance schedules must stay documented as a stable operator contract.

## What Changes

- Replace the Falco platform application with a `falcosidekick` deployment that keeps the UI in-cluster and exposes a stable internal ingest endpoint for Falco events.
- Install the actual Falco sensor on the Proxmox host with the supported `modern_ebpf` host path, and forward events into the cluster-side Falcosidekick ingest service.
- Keep Falco UI protected through shared edge auth while making runtime coverage depend on the host-side sensor path instead of an LXC worker DaemonSet.
- Remove the repo's fail-closed dependency on `haac.io/falco-runtime` worker labels for Falco enablement.
- Make the ephemeral WSL SSH runtime idempotent so repeated `task up` / `verify-cluster` runs do not fail on stale copied key material.
- Document and codify the ownership boundary between Kubernetes CronJobs and Semaphore-managed maintenance schedules.

## Capabilities

### New Capabilities
- `maintenance-job-boundaries`: defines which recurring work belongs in Kubernetes CronJobs and which belongs in Semaphore-managed maintenance schedules.

### Modified Capabilities
- `falco-lxc-readiness`: change Falco from "runtime on declared compatible unprivileged LXC workers" to "runtime supported through a dedicated host-side Falco sensor with cluster-side Falcosidekick ingest and UI".
- `operator-runtime-hygiene`: tighten the WSL runtime requirement so ephemeral SSH artifacts are recreated idempotently on rerun instead of failing on stale copies.

## Impact

- Affected code: `scripts/haac.py`, `scripts/haaclib/gitops.py`
- Affected GitOps: `k8s/platform/applications/falco-app.yaml.template`, rendered output, and a new cluster-side Falco ingest service manifest
- Affected Ansible: `ansible/playbook.yml`
- Affected operator inputs/docs: `.env.example`, `README.md`, `ARCHITECTURE.md`
- Affected stable specs: `openspec/specs/falco-lxc-readiness/`, `openspec/specs/operator-runtime-hygiene/`
