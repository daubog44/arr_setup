## MODIFIED Requirements

### Requirement: Cold bootstrap child applications must tolerate CRD ordering

Platform child applications that render custom resources from CRDs installed by sibling applications MUST not fail the cold `task up` path only because the CRD appears later in the same bootstrap window.

#### Scenario: Alloy tolerates a missing ServiceMonitor CRD during cold sync planning

- **WHEN** the cluster is rebuilt from `down` and the `alloy` application renders its `ServiceMonitor`
- **THEN** ArgoCD MUST tolerate the CRD arriving later in the same cold bootstrap sequence
- **AND** the `alloy` application MUST not fail with `one or more synchronization tasks are not valid`
