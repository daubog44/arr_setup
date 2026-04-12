## 1. Implementation

- [x] 1.1 Gate GitOps bootstrap on cluster-side flannel readiness plus essential `kube-system` deployments before Sealed Secrets is installed
- [x] 1.2 Fail Sealed Secrets rollout with deployment, pod, log, and event diagnostics when the controller still does not converge

## 2. Validation

- [x] 2.1 Validate with `openspec validate gate-gitops-on-kube-system-core`, Ansible syntax checks, `python scripts/haac.py check-env`, `python scripts/haac.py doctor`, and `python scripts/haac.py task-run -- -n up`
- [x] 2.2 Rerun `configure-os` or `task up` live and record whether the new pre-GitOps gate or Sealed Secrets rescue reports the remaining blocker explicitly
