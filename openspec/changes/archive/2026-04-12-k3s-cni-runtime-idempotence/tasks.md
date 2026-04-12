## 1. Implementation

- [x] 1.1 Remove the duplicated worker NVIDIA runtime reconciliation path and stop forcing `default-runtime: nvidia`
- [x] 1.2 Restart `k3s` / `k3s-agent` only on real config or runtime drift, without hiding worker restart failures
- [x] 1.3 Add an explicit K3s CNI and node-readiness gate before GitOps bootstrap
- [x] 1.4 Add a cluster `RuntimeClass` for NVIDIA and move the tracked GPU workload to explicit `runtimeClassName: nvidia`

## 2. Validation

- [x] 2.1 Validate the change with `openspec validate k3s-cni-runtime-idempotence`, Ansible syntax checks, `python scripts/haac.py check-env`, `python scripts/haac.py doctor`, `helm template`, and `python scripts/haac.py task-run -- -n up`
- [x] 2.2 Rerun `configure-os` or `task up` in the live environment and record whether the cluster passes the new K3s/CNI gate or fails with clearer readiness diagnostics
