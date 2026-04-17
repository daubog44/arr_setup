# cluster-policy-baseline Specification

## Purpose
Keep a small repo-managed Kubernetes policy baseline in place so admission posture, namespace PSA intent, and policy visibility do not depend on manual cluster state.

## Requirements
### Requirement: Cluster policy baseline is repo-managed
The repository MUST manage a baseline Kubernetes policy layer instead of relying only on app-by-app hardening.

#### Scenario: Cluster policy baseline is reconciled
- **WHEN** the platform layer is rendered
- **THEN** it MUST include a repo-managed Kyverno installation
- **AND** it MUST include a documented baseline set of admission policies with explicit exceptions for workloads that need elevated behavior

### Requirement: Policy results have an in-cluster UI
Policy violations and passes MUST be visible through a repo-managed in-cluster reporting UI.

#### Scenario: Policy reporting surface is published
- **WHEN** the policy reporting UI is intentionally enabled
- **THEN** the repo MUST publish a web UI backed by policy reports for the cluster
- **AND** that UI MUST integrate Kyverno policy results

### Requirement: Namespace security labels are declared repo-side
Pod Security Admission labels MUST be declared at namespace creation time instead of being left implicit.

#### Scenario: Managed namespaces are rendered
- **WHEN** bootstrap root namespaces are rendered
- **THEN** each managed namespace MUST declare its intended Pod Security Admission posture
- **AND** exceptions MUST be explicit rather than accidental
