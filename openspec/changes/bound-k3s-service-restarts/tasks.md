## 1. Implementation

- [x] 1.1 Add a bounded K3s service recovery helper that restarts `k3s` or `k3s-agent` without indefinite blocking and captures service diagnostics on timeout
- [x] 1.2 Wire the bounded recovery path into the K3s restart tasks and handlers in `ansible/playbook.yml`

## 2. Validation

- [x] 2.1 Validate the change with `openspec validate bound-k3s-service-restarts`, Ansible syntax/readback checks, and dry-run bootstrap evidence
- [x] 2.2 When the live environment is available, rerun `configure-os` or `task up` until node configuration either succeeds or fails with the new bounded K3s recovery output; record the furthest verified phase
