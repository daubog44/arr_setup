## ADDED Requirements

### Requirement: Single command bootstrap
The system MUST provide a single supported bootstrap command that orchestrates infrastructure provisioning, node configuration, GitOps bootstrap, and cluster verification for the homelab stack.

#### Scenario: Supported bootstrap entrypoint
- **WHEN** an operator wants to create or reconcile the homelab from the repository
- **THEN** the supported entrypoint MUST be `task up` or a wrapper that invokes the same pipeline

#### Scenario: Shared orchestration contract
- **WHEN** the operator runs `task up`, `.\haac.ps1 up`, or `sh ./haac.sh up`
- **THEN** each entrypoint MUST execute the same bootstrap phases in the same logical order

### Requirement: Bootstrap phase visibility
The system MUST expose the phase structure of the bootstrap pipeline so operators can identify where a run is currently executing and where a failure occurred.

#### Scenario: Phase-oriented execution
- **WHEN** the bootstrap command runs
- **THEN** it MUST progress through explicit phases covering preflight, provisioning, configuration, GitOps bootstrap, publication, and verification

#### Scenario: Failure attribution
- **WHEN** a bootstrap phase fails
- **THEN** the operator output MUST identify the failing phase and point to the relevant command or component to inspect next

### Requirement: Public service URL reporting
The system MUST produce a final public endpoint report for the services exposed through the homelab ingress and Cloudflare path.

#### Scenario: Successful endpoint summary
- **WHEN** bootstrap succeeds
- **THEN** the final output MUST include the list of visitable public URLs with service name, namespace, auth expectation, and verification status

#### Scenario: Endpoint source of truth
- **WHEN** the system builds the public endpoint report
- **THEN** it MUST derive URLs from one configured source of truth rather than maintaining an unrelated duplicated list

### Requirement: Endpoint verification gating
The system MUST verify public URLs only after the prerequisites for exposure are satisfied.

#### Scenario: Readiness before public verification
- **WHEN** endpoint verification begins
- **THEN** the system MUST have already completed the readiness stages required for GitOps reconciliation and public routing publication

#### Scenario: Partial endpoint failure
- **WHEN** one or more public endpoints are not reachable
- **THEN** the bootstrap output MUST identify which endpoints failed and preserve the status of the endpoints that passed

### Requirement: Browser-level endpoint verification
The system MUST support browser-level verification of the final public URLs in addition to HTTP-level reachability checks when the operator workflow is being validated through the autonomous loop.

#### Scenario: Public URL verification through the loop
- **WHEN** the autonomous loop validates the final public endpoint report
- **THEN** it MUST use Playwright MCP to navigate the emitted URLs when Playwright MCP is available and report whether each URL is actually navigable or redirected to the expected auth flow

### Requirement: Preflight input validation
The system MUST validate the minimum local and environment prerequisites needed to start the bootstrap safely.

#### Scenario: Missing required input
- **WHEN** a required `.env` input or local prerequisite is missing
- **THEN** the bootstrap command MUST fail before infrastructure provisioning begins

#### Scenario: Remote prerequisite failure
- **WHEN** a required remote dependency for bootstrap is unreachable or unauthorized
- **THEN** the preflight stage MUST report that condition before continuing to later phases
