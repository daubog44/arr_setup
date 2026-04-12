## MODIFIED Requirements

### Requirement: Preflight input validation
The system MUST validate the minimum local and environment prerequisites needed to start the bootstrap safely, including the workstation-reachable Proxmox access host used for API and SSH operations.

#### Scenario: Missing required input
- **WHEN** a required `.env` input or local prerequisite is missing
- **THEN** the bootstrap command MUST fail before infrastructure provisioning begins

#### Scenario: Remote prerequisite failure
- **WHEN** a required remote dependency for bootstrap is unreachable or unauthorized
- **THEN** the preflight stage MUST report that condition before continuing to later phases

#### Scenario: Separate access host for non-resolvable node names
- **WHEN** `MASTER_TARGET_NODE` is a valid Proxmox node identifier but is not itself resolvable from the operator workstation
- **THEN** the bootstrap contract MUST allow a separate Proxmox access host input and preflight MUST validate that effective access host before provisioning begins
