# semaphore-bootstrap-readiness Specification

## Purpose
TBD - created by archiving change stabilize-semaphore-bootstrap-readiness. Update Purpose after archive.
## Requirements
### Requirement: Semaphore Application values MUST match the official chart schema

The repo MUST render the Semaphore ArgoCD Application with values that the official Semaphore chart version actually consumes.

#### Scenario: Rendered Semaphore workload uses the declared database backend
- **WHEN** the Semaphore Application renders the official chart version pinned in the repo
- **THEN** the rendered Deployment MUST use the declared non-default database backend instead of silently falling back to the chart default `bolt`

#### Scenario: Chart-managed local admin uses the generated secret contract
- **WHEN** the Application enables chart-managed local admin creation
- **THEN** the referenced secret MUST contain the admin username, password, email, and fullname keys expected by the official chart

### Requirement: Public Semaphore access MUST stay protected without embedding raw OIDC secrets in tracked manifests

The repo MUST protect the public Semaphore route while avoiding unsupported OIDC secret-ref shapes in the chart values.

#### Scenario: Public route uses the cluster auth middleware chain
- **WHEN** the Semaphore public route is rendered
- **THEN** the route MUST apply the existing `force-https` and `authelia` middlewares from the `mgmt` namespace

#### Scenario: Unsupported chart OIDC secret refs are not used
- **WHEN** the Semaphore Application is rendered
- **THEN** it MUST NOT rely on chart values that require embedding a raw OIDC client secret into tracked GitOps manifests

### Requirement: Semaphore bootstrap MUST be rerunnable without Helm hook drift

The Semaphore bootstrap resource MUST reconcile as a normal Argo-managed Job instead of a Helm hook so the GitOps readiness phase can observe it deterministically.

#### Scenario: ArgoCD tracks the bootstrap Job as a normal resource
- **WHEN** `haac-stack` reconciles
- **THEN** `semaphore-bootstrap` MUST be rendered without Helm hook annotations that keep the application operation stuck on hook bookkeeping

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
