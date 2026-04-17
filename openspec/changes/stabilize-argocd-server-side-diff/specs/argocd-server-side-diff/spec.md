## ADDED Requirements

### Requirement: GitOps compare uses server-side diff for SSA-driven mutable resources

The repository MUST enable Argo CD server-side diff for repo-managed applications whose live resources depend on server-side apply, Kubernetes defaulting, or controller mutation in ways that would otherwise keep them falsely `OutOfSync`.

#### Scenario: Live resources are semantically equal after server-side apply

- **WHEN** an Argo CD application manages resources such as CRDs, `ServiceMonitor`s, or `StatefulSet`s that gain server-side defaults or controller-owned fields
- **AND** server-side dry-run compare shows no semantic drift
- **THEN** the repo-managed `Application` manifest MUST opt into Argo CD server-side diff for that application
- **AND** `task up` verification MUST be able to report those applications as `Synced` instead of leaving persistent false drift
