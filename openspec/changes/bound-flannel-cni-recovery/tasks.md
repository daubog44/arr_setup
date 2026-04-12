## 1. Implementation

- [ ] 1.1 Extend the flannel readiness helper to capture cluster-side flannel workload state for the failing node from the master
- [ ] 1.2 Add one bounded flannel-specific recovery attempt after the existing K3s service restart, then re-check `/run/flannel/subnet.env`

## 2. Validation

- [ ] 2.1 Validate with `openspec validate bound-flannel-cni-recovery`, Ansible syntax checks, `python scripts/haac.py check-env`, `python scripts/haac.py doctor`, and `python scripts/haac.py task-run -- -n up`
- [ ] 2.2 Rerun `configure-os` or `task up` live and record whether flannel recovers or fails with combined node-local plus cluster-side diagnostics
