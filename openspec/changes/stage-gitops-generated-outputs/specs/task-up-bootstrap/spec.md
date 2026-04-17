## MODIFIED Requirements

### Requirement: GitOps publication is complete

The system MUST publish the repo-managed outputs needed for ArgoCD to converge on the current cluster state.

#### Scenario: Bootstrap republishes generated platform secrets

- **WHEN** `task up` regenerates sealed outputs for the current cluster before GitOps publication
- **THEN** the publication phase MUST stage and push those regenerated platform secrets instead of leaving them local-only
- **AND** the platform root gate MUST NOT fail because Git still carries a stale generated SealedSecret from a previous cluster state
