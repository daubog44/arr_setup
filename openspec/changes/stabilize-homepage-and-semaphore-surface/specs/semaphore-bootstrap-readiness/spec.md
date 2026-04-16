## MODIFIED Requirements

### Requirement: Semaphore bootstrap MUST be rerunnable without Helm hook drift

The Semaphore bootstrap resource MUST reconcile as a normal Argo-managed Job instead of a Helm hook so the GitOps readiness phase can observe it deterministically.

#### Scenario: Bootstrap job can be recreated on subsequent syncs

- **WHEN** a later sync needs to rerun the bootstrap Job
- **THEN** ArgoCD MUST be able to replace the existing Job resource without requiring a manual live patch
- **AND** changes to the repo-managed bootstrap script MUST force a new Job template revision

### Requirement: Bootstrap-created recurring jobs are active and operator-visible

Semaphore bootstrap MUST create the repo-managed recurring maintenance schedules as active schedules.

#### Scenario: Maintenance schedules are reconciled

- **WHEN** the bootstrap job reconciles the managed maintenance templates
- **THEN** the generated schedules MUST be stored as `active`
- **AND** they MUST remain visible from the owning project in the Semaphore UI
- **AND** each schedule MUST keep a stable repo-managed display name
