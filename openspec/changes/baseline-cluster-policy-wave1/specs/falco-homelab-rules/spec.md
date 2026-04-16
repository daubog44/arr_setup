## ADDED Requirements

### Requirement: Falco ships a repo-managed homelab rule baseline
Enabled Falco MUST include a curated rule baseline for common homelab abuse paths.

#### Scenario: Falco is enabled
- **WHEN** the operator enables Falco for this environment
- **THEN** the repo-managed configuration MUST provide a curated rule bundle for suspicious shells, package managers, writes to sensitive paths, socket abuse, SSH material access, and similar high-signal homelab events

### Requirement: Falco rule reconciliation belongs to post-install security
Falco rule assets MUST be reconciled through a dedicated post-install security path instead of being mixed into unrelated operator tasks.

#### Scenario: Security post-install runs
- **WHEN** the post-install security phase runs
- **THEN** it MUST reconcile the repo-managed Falco rule assets needed by the supported host-side sensor path
