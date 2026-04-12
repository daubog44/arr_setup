# task-up-idempotence Specification

## Purpose
TBD - created by archiving change task-up-idempotent-bootstrap. Update Purpose after archive.
## Requirements
### Requirement: Task Up Is Safe To Re-run
The system SHALL treat `task up` as a convergent reconciliation command, not as a one-shot bootstrap that assumes a clean environment every time.

#### Scenario: Infra already converged
- **WHEN** the target infrastructure already matches the declared OpenTofu state
- **THEN** rerunning `task up` MUST reuse that state without requiring a destroy step or proposing destructive drift as the normal path

#### Scenario: Platform already bootstrapped
- **WHEN** ArgoCD, platform applications, workloads, or Cloudflare publication already exist from a previous successful or partial run
- **THEN** rerunning `task up` MUST reconcile those phases without failing solely because the resources already exist

### Requirement: Task Up Avoids Duplicate Side Effects
The system SHALL avoid duplicate operator-visible side effects when the desired state has not changed between runs.

#### Scenario: GitOps output unchanged
- **WHEN** the rendered GitOps artifacts and secrets are unchanged on a rerun
- **THEN** the GitOps publication phase MUST complete without requiring a synthetic empty commit or other duplicate publish action

#### Scenario: Cloudflare already aligned
- **WHEN** the desired tunnel ingress and DNS records already exist and match the declared configuration
- **THEN** the Cloudflare phase MUST report convergence instead of creating duplicate records or failing on pre-existing state

### Requirement: Task Up Reports Phase-Specific Recovery
The system SHALL report failures in terms of explicit bootstrap phases and preserve enough information for a safe rerun decision.

#### Scenario: Failure after a completed earlier phase
- **WHEN** a later phase fails after one or more earlier phases completed successfully
- **THEN** the operator output MUST identify the last verified phase and the failing phase so the next `task up` rerun can be evaluated as a recovery step

#### Scenario: Retryable gate timeout
- **WHEN** a retrying readiness or verification gate times out
- **THEN** the failure output MUST name the exact gate, the last successful checkpoint, and whether earlier convergent phases need no manual reset

