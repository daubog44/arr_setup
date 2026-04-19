## ADDED Requirements

### Requirement: Repo-managed child Applications recover from missing-hook stalls

The operator MUST recover repo-managed child Applications that remain stuck on a missing hook resource at the current desired revision.

#### Scenario: Same-revision hook job is missing

- **WHEN** an ArgoCD child Application is `Running`
- **AND** its operation message says it is waiting for completion of a hook resource
- **AND** the referenced hook resource is absent from the cluster
- **AND** the Application is managed from the current GitOps repository
- **THEN** the operator MUST treat the Application as hook-stalled
- **AND** it MUST trigger the supported recovery path for that child Application

#### Scenario: Non-repo-managed Application is stalled

- **WHEN** the operator detects the same missing-hook shape on an Application that is not managed from the current GitOps repository
- **THEN** it MUST NOT recycle that Application automatically
- **AND** it MUST report the stall as a manual-intervention case instead
