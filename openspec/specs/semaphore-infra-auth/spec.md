# semaphore-infra-auth Specification

## Purpose
TBD - created by archiving change least-privilege-semaphore-infra-auth. Update Purpose after archive.
## Requirements
### Requirement: Semaphore infrastructure access MUST not rely on a root-equivalent cluster-held SSH key

Semaphore-driven infrastructure maintenance MUST use a dedicated non-root maintenance principal instead of direct root SSH.

#### Scenario: Maintenance inventory is rendered

- **WHEN** the repo renders the inventory used by Semaphore maintenance jobs
- **THEN** Proxmox and guest hosts MUST use the dedicated maintenance principal
- **AND** the maintenance inventory MUST enable `become`
- **AND** the bootstrap inventory used by `task up` MAY still use the operator bootstrap path

#### Scenario: Cluster-held maintenance key is authorized

- **WHEN** the bootstrap playbook provisions SSH authorization on Proxmox and the guests
- **THEN** the Semaphore maintenance public key MUST be authorized only for the maintenance principal
- **AND** it MUST NOT remain present in root `authorized_keys`

### Requirement: Bootstrap root authorization MUST be explicit

The bootstrap playbook MUST not authorize all `haac*.pub` keys on root accounts.

#### Scenario: Root authorization is reconciled

- **WHEN** the bootstrap playbook reconciles Proxmox root or guest root SSH access
- **THEN** it MUST authorize only the explicit operator bootstrap public key required for `task up`
- **AND** it MUST remove stale maintenance-key root authorization introduced by earlier wildcard logic

### Requirement: Semaphore repository auth MUST be separate from infrastructure auth

Semaphore repository access MUST not reuse the same SSH key that reaches infrastructure hosts.

#### Scenario: Public HTTPS repo is configured

- **WHEN** `GITOPS_REPO_URL` is an HTTPS URL that does not require SSH credentials
- **THEN** Semaphore MUST create the repository without reusing the infrastructure maintenance SSH key

#### Scenario: SSH-authenticated repo is configured

- **WHEN** `GITOPS_REPO_URL` requires SSH credentials
- **THEN** Semaphore MUST use a dedicated repo deploy key
- **AND** that key MUST NOT be authorized on Proxmox or guest hosts

### Requirement: Maintenance sudo MUST be limited to repo-managed maintenance commands

The maintenance principal MUST not receive unrestricted passwordless sudo.

#### Scenario: Maintenance principal escalates privileges

- **WHEN** the maintenance principal runs the repo-managed maintenance playbooks
- **THEN** privilege escalation MUST be limited to explicit repo-managed maintenance wrapper commands
- **AND** the maintenance playbooks MUST be compatible with that bounded sudo surface

