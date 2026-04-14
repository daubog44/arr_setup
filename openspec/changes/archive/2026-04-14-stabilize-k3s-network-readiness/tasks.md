## 1. Implementation

- [x] 1.1 Remove cluster-side flannel pod assumptions from the pre-GitOps kube-system readiness gate
- [x] 1.2 Keep the node-local flannel recovery bounded and diagnostics-first
- [x] 1.3 Relax degraded Longhorn admission webhooks during bootstrap recovery only when the service exists with zero endpoints and still fails closed
- [x] 1.4 Restart K3s agents and then the server once after that degraded-webhook recovery path so flannel runtime state can be rebuilt

## 2. Validation

- [x] 2.1 Validate with `ansible-playbook --syntax-check`, `openspec validate stabilize-k3s-network-readiness`, and `python scripts/haac.py task-run -- -n up`
- [x] 2.2 Rerun `configure-os` live and record whether the bootstrap now progresses beyond the corrected readiness gates after the degraded Longhorn webhook recovery path
