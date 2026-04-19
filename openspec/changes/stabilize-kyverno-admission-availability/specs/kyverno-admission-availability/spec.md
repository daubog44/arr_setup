## ADDED Requirements

### Requirement: Kyverno admission keeps a ready endpoint during ordinary pod churn

The repo-managed Kyverno application MUST deploy the admission controller with more than one replica and scheduling guidance that avoids collapsing all replicas onto the same node when cluster capacity exists.

#### Scenario: Admission controller is rendered for high availability

- **WHEN** the Kyverno GitOps application is rendered from the repo-managed template
- **THEN** `admissionController.replicas` is at least `2`
- **AND** the rendered values include topology or anti-affinity guidance for spreading admission replicas across nodes

#### Scenario: GitOps readiness depends on Kyverno admission availability

- **WHEN** `task up` or `wait-for-argocd-sync` reconciles repo-managed Applications
- **THEN** the supported configuration does not rely on a single Kyverno admission replica being continuously ready
- **AND** temporary restart of one admission pod does not leave `kyverno-svc` without any ready endpoint
