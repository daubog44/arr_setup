## MODIFIED Requirements

### Requirement: Cold bootstrap child applications must tolerate CRD ordering

Platform child applications that render custom resources from CRDs installed by sibling applications MUST not fail the cold `task up` path only because the CRD appears later in the same bootstrap window.

#### Scenario: Monitoring child apps recover after Prometheus Operator CRDs appear

- **WHEN** the cluster is rebuilt from `down` and a platform child application renders a `ServiceMonitor` or `PodMonitor` before the Prometheus Operator CRDs are available
- **THEN** ArgoCD MUST tolerate the CRD arriving later in the same cold bootstrap sequence
- **AND** the bootstrap wait path MUST refresh and re-sync the affected child application once the required CRD exists
- **AND** `task up` MUST continue past the monitoring child application gates instead of failing permanently with `one or more synchronization tasks are not valid`
