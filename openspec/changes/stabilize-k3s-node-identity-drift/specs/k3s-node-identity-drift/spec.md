## ADDED Requirements

### Requirement: Unmanaged duplicate K3s node identities are quarantined before node configuration
The system MUST detect unmanaged Proxmox LXC containers that duplicate the hostname or IPv4 identity of a declared K3s node and quarantine them before node configuration proceeds.

#### Scenario: Duplicate unmanaged worker container is running
- **WHEN** a running Proxmox LXC is outside the declared OpenTofu VMID set
- **AND** that LXC reuses the hostname or IPv4 address of a declared K3s master or worker
- **THEN** the system MUST disable `onboot` for the unmanaged duplicate
- **AND** the system MUST stop the unmanaged duplicate container
- **AND** the operator output MUST report which VMID was quarantined and why

### Requirement: Non-duplicate or declared nodes are never quarantined
The system MUST avoid quarantining declared nodes or unrelated unmanaged containers.

#### Scenario: LXC does not collide with declared node identity
- **WHEN** a Proxmox LXC is part of the declared VMID set
- **OR** it does not share a declared hostname or IPv4 address
- **THEN** the system MUST leave that LXC unchanged
