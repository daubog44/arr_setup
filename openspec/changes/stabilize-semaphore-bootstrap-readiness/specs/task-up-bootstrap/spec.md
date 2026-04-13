## MODIFIED Requirements

### Requirement: Single command bootstrap
The system MUST provide a single supported bootstrap command that orchestrates infrastructure provisioning, node configuration, GitOps bootstrap, Cloudflare publication, and cluster verification for the homelab stack, and that same command MUST remain safe to rerun as the normal recovery path.

#### Scenario: Supported bootstrap entrypoint
- **WHEN** an operator wants to create or reconcile the homelab from the repository
- **THEN** the supported entrypoint MUST be `task up` or a wrapper that invokes the same pipeline

#### Scenario: Shared orchestration contract
- **WHEN** the operator runs `task up`, `.\haac.ps1 up`, or `sh ./haac.sh up`
- **THEN** each entrypoint MUST execute the same bootstrap phases in the same logical order

#### Scenario: Supported rerun path
- **WHEN** a previous bootstrap run completed partially or fully
- **THEN** rerunning the same supported bootstrap command MUST be the primary supported recovery path unless the failure message explicitly says manual intervention is required
- **AND** reruns during the GitOps readiness phase MUST NOT depend on clearing stale Helm hook state for Semaphore bootstrap by hand
