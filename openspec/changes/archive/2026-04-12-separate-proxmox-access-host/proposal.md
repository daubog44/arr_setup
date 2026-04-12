## Why

The current bootstrap contract overloads `MASTER_TARGET_NODE` as both the Proxmox node name and the workstation-reachable API/SSH address. That works only when the node name resolves on the operator machine, which is not guaranteed in homelab setups and is currently blocking the live `task up` acceptance proof on Windows.

## What Changes

- Introduce a separate `.env` input for the workstation-reachable Proxmox API/SSH address while keeping `MASTER_TARGET_NODE` as the Proxmox node identity used inside OpenTofu and inventory generation.
- Update bootstrap preflight, OpenTofu provider wiring, and SSH/tunnel helpers to use the new access-host contract without regressing existing environments where the node name itself is already reachable.
- Align operator docs, examples, and validation guidance so the Proxmox access path is explicit before `task up` starts mutating infrastructure.

## Capabilities

### New Capabilities
- `proxmox-access-host`: define the source-of-truth input and runtime behavior for separating Proxmox node identity from the operator-reachable access address.

### Modified Capabilities
- `task-up-bootstrap`: tighten the preflight/bootstrap contract so it validates and uses the Proxmox access host instead of assuming the node name is directly resolvable from the workstation.

## Impact

- Affected bootstrap inputs: `.env.example`, `.env` validation rules, generated Terraform environment mapping
- Affected orchestration logic: `scripts/haac.py`, `Taskfile.yml`
- Affected infrastructure wiring: `tofu/providers.tf`, `tofu/variables.tf`, related templates or outputs that currently assume one Proxmox host field
- Affected operator guidance: `README.md`, `ARCHITECTURE.md`, `docs/runbooks/task-up.md`
