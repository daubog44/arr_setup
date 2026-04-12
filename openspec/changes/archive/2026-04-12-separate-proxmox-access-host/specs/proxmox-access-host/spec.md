## ADDED Requirements

### Requirement: Separate Proxmox node identity from access host
The system MUST let operators declare the Proxmox node name independently from the workstation-reachable API and SSH address used during bootstrap.

#### Scenario: Explicit access host provided
- **WHEN** `.env` sets `MASTER_TARGET_NODE` to the Proxmox node name and `PROXMOX_ACCESS_HOST` to a reachable IP or hostname
- **THEN** bootstrap preflight, Proxmox API access, SSH operations, and tunnel setup MUST use `PROXMOX_ACCESS_HOST` while OpenTofu resources continue using `MASTER_TARGET_NODE` as the node identity

#### Scenario: Backward-compatible fallback
- **WHEN** `.env` does not set `PROXMOX_ACCESS_HOST`
- **THEN** the system MUST fall back to `MASTER_TARGET_NODE` as the effective Proxmox access host so already working environments do not require immediate changes

### Requirement: Access-host failures are operator-visible
The system MUST report Proxmox access-host misconfiguration before bootstrap mutates infrastructure.

#### Scenario: Unreachable access host
- **WHEN** the effective Proxmox access host cannot be resolved or reached on the required API or SSH ports during preflight
- **THEN** the bootstrap command MUST fail in preflight and direct the operator to `PROXMOX_ACCESS_HOST` or the effective access-host setting instead of proceeding to provisioning
