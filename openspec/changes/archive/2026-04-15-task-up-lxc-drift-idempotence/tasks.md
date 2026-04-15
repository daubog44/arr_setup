## 1. Implementation

- [ ] 1.1 Add a declared-container fingerprint to the LXC module so bootstrap-spec changes are explicit
- [ ] 1.2 Make the Proxmox LXC resource ignore unsafe in-place drift that comes from later HaaC LXC reconciliation
- [ ] 1.3 Make `task up` use the state-safe OpenTofu apply path while keeping `task plan` as the full-refresh diagnostic path

## 2. Validation

- [ ] 2.1 Validate with `python scripts/haac.py run-tofu --dir tofu plan -refresh=false -no-color` and confirm the bootstrap path is a no-op
- [ ] 2.2 Validate with `python scripts/haac.py task-run -- -n up`
- [ ] 2.3 Rerun `task up` live and record the next verified phase or the next real blocker after `provision-infra`
