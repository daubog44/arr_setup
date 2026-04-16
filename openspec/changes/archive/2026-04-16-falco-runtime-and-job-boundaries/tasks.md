## 1. OpenSpec and contracts

- [x] 1.1 Rewrite the proposal, design, and delta specs so the change describes the supported host-side Falco sensor plus cluster-side Falcosidekick model
- [x] 1.2 Update the stable docs so recurring Kubernetes CronJobs versus Semaphore schedules are explained as an intentional execution-boundary split

## 2. Runtime and operator implementation

- [x] 2.1 Keep the WSL runtime SSH material idempotent on rerun in `scripts/haac.py`
- [x] 2.2 Replace the in-cluster Falco sensor application with a cluster-side `falcosidekick` deployment plus a stable ingest service derived from repo source of truth
- [x] 2.3 Install and configure the real Falco sensor on the Proxmox host using `modern_ebpf` and `http_output` toward the cluster-side ingest endpoint
- [x] 2.4 Remove the bootstrap fail-closed dependency on `haac.io/falco-runtime` worker labels while preserving the documented CronJob vs Semaphore boundary

## 3. Validation

- [x] 3.1 Re-render and validate manifests locally with `helm template`, `kubectl kustomize`, and `task -n up`
- [x] 3.2 Reconcile the live cluster, verify Falcosidekick UI plus Proxmox-host Falco service health, and capture the resulting runtime and recurring-job state
