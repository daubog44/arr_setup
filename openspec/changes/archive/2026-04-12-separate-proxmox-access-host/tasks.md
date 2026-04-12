## 1. Input And Bootstrap Wiring

- [x] 1.1 Add `PROXMOX_ACCESS_HOST` to the environment contract and central helper logic in `scripts/haac.py`
- [x] 1.2 Update OpenTofu and Task bootstrap plumbing so API, SSH, and tunnel operations use the effective Proxmox access host without changing node-name semantics

## 2. Operator Guidance

- [x] 2.1 Update `.env.example`, `README.md`, `ARCHITECTURE.md`, and `docs/runbooks/task-up.md` to explain the separate Proxmox access host contract and fallback behavior

## 3. Validation

- [x] 3.1 Validate the change with `openspec validate separate-proxmox-access-host`, Python compile checks, `task -n up`, and focused `check-env` or helper checks for access-host resolution
- [x] 3.2 Retry the blocked live `task up` acceptance path if a real `PROXMOX_ACCESS_HOST` is available; otherwise record the exact remaining environment prerequisite
