# argocd-head-revision-readiness Specification

## ADDED Requirements

### Requirement: Repo-managed readiness gates require the expected Git revision

Repo-managed ArgoCD applications MUST not satisfy bootstrap readiness while they are only healthy on an older Git revision than the one published by the operator flow.

#### Scenario: ArgoCD application is healthy but stale

- **WHEN** a repo-managed ArgoCD application reports `Synced` and `Healthy`
- **AND** its `status.sync.revision` does not match the expected GitOps revision from the configured remote branch
- **THEN** the readiness gate MUST keep waiting instead of reporting success
- **AND** the bootstrap logic MUST request a hard refresh so ArgoCD re-resolves the branch head

#### Scenario: Root application just got reapplied

- **WHEN** the bootstrap path reapplies the repo-owned root ArgoCD application
- **THEN** it MUST trigger a refresh for that root application before later readiness gates evaluate child applications
