## 1. Implementation

- [ ] 1.1 Re-check master local flannel state immediately before Sealed Secrets and ArgoCD bootstrap installs
- [ ] 1.2 Refresh degraded Longhorn webhook fail-open immediately before bounded master `k3s` restart recovery inside the flannel wait task
- [ ] 1.3 Extract node-label reconciliation into a reusable task and defer it until after ArgoCD bootstrap is stable

## 2. Validation

- [ ] 2.1 Validate with `ansible-playbook --syntax-check`, `openspec validate recover-master-flannel-before-gitops`, and `python scripts/haac.py task-run -- -n up`
- [ ] 2.2 Rerun `configure-os` live and record whether bootstrap progresses beyond the Sealed Secrets timeout with the master flannel recheck in place
- [ ] 2.3 If `configure-os` passes, rerun `task up` end-to-end and record the furthest verified phase and final blocking point, if any
