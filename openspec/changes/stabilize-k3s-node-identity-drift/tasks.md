## 1. Detection and quarantine

- [ ] 1.1 Add `scripts/haac.py` helpers to load declared K3s node identities from OpenTofu outputs and inspect live Proxmox LXC configs
- [ ] 1.2 Add a safe quarantine path that disables `onboot` and stops unmanaged duplicate LXCs that collide on declared hostname or IPv4

## 2. Bootstrap integration

- [ ] 2.1 Invoke the duplicate-identity repair automatically before the Ansible `configure-os` path and expose an explicit CLI entrypoint
- [ ] 2.2 Add focused regression coverage for declared-vs-live matching and quarantine decisions

## 3. Validation

- [ ] 3.1 Validate with OpenSpec plus targeted unit tests
- [ ] 3.2 Validate live by quarantining the current duplicate worker LXCs, rerunning `configure-os`, and rerunning downstream GitOps/media checks
