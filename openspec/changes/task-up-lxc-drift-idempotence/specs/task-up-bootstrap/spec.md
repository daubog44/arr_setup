## MODIFIED Requirements

### Requirement: task up does not strip HaaC-managed LXC runtime config on rerun

The `task up` bootstrap path MUST NOT mutate an already-converged Proxmox LXC container in a way that removes HaaC-managed runtime config lines which are reconciled outside the Proxmox provider schema.

#### Scenario: converged cluster reruns provisioning with unchanged inputs

- **WHEN** the declared `.env` and module-backed LXC bootstrap inputs are unchanged
- **AND** the existing LXC config already contains HaaC-managed `idmap` or other runtime compatibility lines that the provider cannot model directly
- **THEN** the `task up` provisioning path does not perform an in-place update that removes those lines
- **AND** `task up` can continue past `provision-infra` without reopening that Proxmox drift
- **AND** a separate full-refresh diagnostic plan may still report unsupported remote drift

### Requirement: declared LXC bootstrap changes remain explicit

When the declared LXC bootstrap spec changes, HaaC MUST treat that as an explicit container replacement boundary rather than an unsafe in-place mutation.

#### Scenario: operator changes a declared LXC bootstrap field

- **WHEN** the declared container bootstrap spec changes for a node
- **THEN** OpenTofu detects that the declaration changed
- **AND** the container is handled as a replacement boundary instead of an in-place update that could silently drop out-of-schema runtime config
