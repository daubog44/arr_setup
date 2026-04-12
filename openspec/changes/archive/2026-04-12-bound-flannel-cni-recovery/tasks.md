## 1. Implementation

- [x] 1.1 Extend the flannel readiness helper to capture cluster-side flannel workload state for the failing node from the master
- [x] 1.2 Add one bounded flannel-specific recovery attempt after the existing K3s service restart, then re-check `/run/flannel/subnet.env`
- [x] 1.3 Gate GitOps bootstrap on recovered cluster-side flannel plus essential `kube-system` workload readiness before Sealed Secrets is installed

## 2. Validation

- [x] 2.1 Validate with `openspec validate bound-flannel-cni-recovery`, Ansible syntax checks, `python scripts/haac.py check-env`, `python scripts/haac.py doctor`, and `python scripts/haac.py task-run -- -n up`
- [ ] 2.2 Rerun `configure-os` or `task up` live and record whether flannel recovers or, if bootstrap still stops, whether the new pre-GitOps gate or Sealed Secrets rescue reports the remaining blocker explicitly
