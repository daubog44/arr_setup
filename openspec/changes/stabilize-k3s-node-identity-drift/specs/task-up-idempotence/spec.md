## MODIFIED Requirements

### Requirement: Task Up Is Safe To Re-run
The system SHALL treat `task up` as a convergent reconciliation command, not as a one-shot bootstrap that assumes a clean environment every time.

#### Scenario: Infra already converged
- **WHEN** the target infrastructure already matches the declared OpenTofu state
- **THEN** rerunning `task up` MUST reuse that state without requiring a destroy step or proposing destructive drift as the normal path

#### Scenario: Platform already bootstrapped
- **WHEN** ArgoCD, platform applications, workloads, or Cloudflare publication already exist from a previous successful or partial run
- **THEN** rerunning `task up` MUST reconcile those phases without failing solely because the resources already exist

#### Scenario: Duplicate unmanaged K3s node identity exists
- **WHEN** the declared OpenTofu node set is already known
- **AND** Proxmox still has an unmanaged LXC that duplicates the hostname or IPv4 identity of a declared K3s node
- **THEN** rerunning `task up` or `task configure-os` MUST quarantine the unmanaged duplicate before continuing node configuration
- **AND** the supported rerun path MUST NOT require manual Proxmox forensics just to restore one-to-one node identity
