## 1. Implementation

- [ ] 1.1 Add a declared-container fingerprint to the LXC module so bootstrap-spec changes are explicit
- [ ] 1.2 Make the Proxmox LXC resource ignore unsafe in-place drift that comes from later HaaC LXC reconciliation

## 2. Validation

- [ ] 2.1 Validate with `python scripts/haac.py run-tofu --dir tofu plan -no-color` and confirm the `idmap` removals disappear
- [ ] 2.2 Validate with `python scripts/haac.py task-run -- -n up`
- [ ] 2.3 Rerun `task up` live and record the next verified phase or the next real blocker after `provision-infra`
