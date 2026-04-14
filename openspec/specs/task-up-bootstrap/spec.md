# task-up-bootstrap Specification

## Purpose
Define the stable operator contract for the one-command `task up` bootstrap path, including phase visibility, preflight checks, and public URL reporting.
## Requirements
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

### Requirement: Bootstrap phase visibility

The system MUST expose the phase structure of the bootstrap pipeline so operators can identify where a run is currently executing and where a failure occurred.

#### Scenario: Failure attribution

- **WHEN** a bootstrap phase fails
- **THEN** the operator output MUST identify the failing phase and point to the relevant command or component to inspect next
- **AND** failures caused by K3s node or CNI readiness MUST be reported as `Node configuration` failures instead of first surfacing as later GitOps rollout errors

#### Scenario: Sealed Secrets rollout does not converge after pre-bootstrap gates pass

- **WHEN** the stronger pre-GitOps readiness gates pass but the Sealed Secrets controller still does not become Available
- **THEN** the bootstrap MUST fail with controller-specific deployment, pod, log, and recent event diagnostics instead of only a generic rollout timeout

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

#### Scenario: Supporting commands reuse the documented password source of truth
- **WHEN** `.env` defines `LXC_PASSWORD` and the caller does not explicitly provide `PROXMOX_HOST_PASSWORD`
- **THEN** the orchestration layer MUST derive the effective Proxmox host password from `LXC_PASSWORD` for supporting bootstrap commands and generated inventory consumers
- **AND** the operator contract MUST not require a second documented `.env` password field just to satisfy those supporting commands

### Requirement: Safe Default Git Publication

`task up` MUST default to publishing only generated GitOps artifacts, not arbitrary local repo changes.

#### Scenario: Clean workspace and default publication

- **WHEN** the operator runs `task up` with the default `PUSH_ALL` value
- **THEN** only generated GitOps artifacts are staged and committed during publication
- **AND** unrelated local work is not auto-committed

#### Scenario: Dirty workspace with unrelated changes and safe default

- **WHEN** the operator runs `task up` with `PUSH_ALL=false` and the repo has unrelated local changes
- **THEN** the bootstrap MUST fail before publication with an explicit message
- **AND** the operator MAY rerun with `PUSH_ALL=true` if they intentionally want wide publication

### Requirement: Redacted Failure Output

Bootstrap failures MUST redact known secret values from surfaced command output.

#### Scenario: Secret-bearing command fails

- **WHEN** a command containing secret-derived values fails
- **THEN** the raised error and printed detail MUST not include the raw secret values

### Requirement: Repo-Owned ArgoCD Bootstrap

The first bootstrap of ArgoCD MUST come from repo-local manifests, not a remote install URL.

#### Scenario: Fresh cluster bootstrap

- **WHEN** `deploy-argocd` bootstraps ArgoCD on a fresh cluster
- **THEN** it MUST apply the vendored local bootstrap manifests from the repo
- **AND** the self-management GitOps application MUST take over afterward

### Requirement: Explicit Authelia Admin Password Input

The operator MUST be able to define the Authelia admin password explicitly in `.env`.

#### Scenario: Plain Authelia password is present

- **WHEN** `AUTHELIA_ADMIN_PASSWORD` is present in `.env`
- **THEN** the generated Authelia users file MUST contain a derived password hash for that password
- **AND** the plain password MUST remain the operator-facing source of truth

### Requirement: Platform Clean Convergence

The platform application set MUST converge without the known `node-problem-detector` and `litmus` drift.

#### Scenario: Platform reconciliation after bootstrap

- **WHEN** ArgoCD reconciles platform applications
- **THEN** `node-problem-detector` MUST not fail from a duplicate `NODE_NAME` env entry
- **AND** `litmus` MUST not remain out of sync because of an oversized MongoDB replica topology

