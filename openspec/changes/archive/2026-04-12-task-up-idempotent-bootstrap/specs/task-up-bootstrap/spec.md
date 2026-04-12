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

### Requirement: Bootstrap phase visibility
The system MUST expose the phase structure of the bootstrap pipeline so operators can identify where a run is currently executing, which phases already converged, and where a failure occurred.

#### Scenario: Phase-oriented execution
- **WHEN** the bootstrap command runs
- **THEN** it MUST progress through explicit phases covering preflight, provisioning, configuration, GitOps bootstrap, publication, and verification

#### Scenario: Failure attribution
- **WHEN** a bootstrap phase fails
- **THEN** the operator output MUST identify the failing phase and point to the relevant command or component to inspect next

#### Scenario: Last verified phase
- **WHEN** a bootstrap phase fails after one or more earlier phases completed
- **THEN** the operator output MUST identify the last verified phase so a rerun decision is explicit
