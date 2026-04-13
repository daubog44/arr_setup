## ADDED Requirements

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
