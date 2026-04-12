## 1. Implementation

- [x] 1.1 Replace the destructive line-by-line LXC hardware reconciliation with canonical HAAC-managed `lxc.*` line reconciliation in `ansible/playbook.yml`
- [x] 1.2 Add a legacy cleanup path that removes unmanaged duplicates and stale marker remnants without reintroducing rerun drift
- [x] 1.3 Keep the LXC restart conditional on real managed-line drift only

## 2. Validation

- [x] 2.1 Validate with `openspec validate idempotent-lxc-hardware-mapping`, Ansible syntax checks, and `python scripts/haac.py task-run -- -n up`
- [x] 2.2 Rerun `configure-os` live twice and record that the second rerun does not restart the LXC containers solely because of the hardware mapping section
