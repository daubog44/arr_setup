## 1. Detection and quarantine

- [x] 1.1 Add `scripts/haac.py` helpers to load declared K3s node identities from OpenTofu outputs and inspect live Proxmox LXC configs
- [x] 1.2 Add a safe quarantine path that disables `onboot` and stops unmanaged duplicate LXCs that collide on declared hostname or IPv4

## 2. Bootstrap integration

- [x] 2.1 Invoke the duplicate-identity repair automatically before the Ansible `configure-os` path and expose an explicit CLI entrypoint
- [x] 2.2 Add focused regression coverage for declared-vs-live matching and quarantine decisions

## 3. Validation

- [x] 3.1 Validate with OpenSpec plus targeted unit tests
- [x] 3.2 Validate live by quarantining the current duplicate worker LXCs, rerunning `configure-os`, and rerunning downstream GitOps/media checks
