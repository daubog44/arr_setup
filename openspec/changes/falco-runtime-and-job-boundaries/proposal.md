## Why

Falco is currently published as a healthy UI while the runtime sensor path is still modeled as unsupported on the default unprivileged Proxmox LXC nodes. At the same time, the Windows WSL bridge has a real rerun bug in the ephemeral SSH runtime path, and the split between in-cluster CronJobs and Semaphore maintenance schedules is not documented as a stable operator contract.

## What Changes

- Switch the Falco runtime profile from the failing `modern_ebpf` path to the compatible `ebpf` path for this environment.
- Keep Falco UI protected through shared edge auth, but require source-of-truth runtime node selection when Falco is enabled.
- Fail closed if Falco is enabled without any declared runtime-capable worker nodes.
- Make the ephemeral WSL SSH runtime idempotent so repeated `task up` / `verify-cluster` runs do not fail on stale copied key material.
- Document and codify the ownership boundary between Kubernetes CronJobs and Semaphore-managed maintenance schedules.

## Capabilities

### New Capabilities
- `maintenance-job-boundaries`: defines which recurring work belongs in Kubernetes CronJobs and which belongs in Semaphore-managed maintenance schedules.

### Modified Capabilities
- `falco-lxc-readiness`: change Falco from "UI only unless unsupported" to "runtime supported on declared compatible unprivileged LXC workers using the compatible probe path".
- `operator-runtime-hygiene`: tighten the WSL runtime requirement so ephemeral SSH artifacts are recreated idempotently on rerun instead of failing on stale copies.

## Impact

- Affected code: `scripts/haac.py`, `scripts/haaclib/gitops.py`
- Affected GitOps: `k8s/platform/applications/falco-app.yaml.template` and rendered output
- Affected operator inputs/docs: `.env.example`, `README.md`, `ARCHITECTURE.md`
- Affected stable specs: `openspec/specs/falco-lxc-readiness/`, `openspec/specs/operator-runtime-hygiene/`
