## 1. OpenSpec and contracts

- [ ] 1.1 Write the proposal, design, and delta specs for Falco runtime readiness, operator runtime hygiene, and recurring-job boundaries
- [ ] 1.2 Update the stable docs so recurring Kubernetes CronJobs versus Semaphore schedules are explained as an intentional execution-boundary split

## 2. Runtime and operator implementation

- [ ] 2.1 Make the WSL runtime SSH material idempotent on rerun in `scripts/haac.py`
- [ ] 2.2 Add source-of-truth validation for Falco runtime-capable worker selection when Falco is enabled
- [ ] 2.3 Switch the Falco GitOps template to the compatible `ebpf` driver path and keep runtime scheduling bound to declared worker labels

## 3. Validation

- [ ] 3.1 Re-render and validate manifests locally with `helm template`, `kubectl kustomize`, and `task -n up`
- [ ] 3.2 Reconcile the live cluster, verify Falco rollout on the declared worker, and capture the resulting runtime and recurring-job state
