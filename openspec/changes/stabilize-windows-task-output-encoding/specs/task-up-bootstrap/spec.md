## MODIFIED Requirements

### Requirement: Bootstrap phase visibility

The system MUST expose the phase structure of the bootstrap pipeline so operators can identify where a run is currently executing and where a failure occurred.

#### Scenario: Failure attribution

- **WHEN** a bootstrap phase fails
- **THEN** the operator output MUST identify the failing phase and point to the relevant command or component to inspect next
- **AND** failures caused by K3s node or CNI readiness MUST be reported as `Node configuration` failures instead of first surfacing as later GitOps rollout errors

#### Scenario: Sealed Secrets rollout does not converge after pre-bootstrap gates pass

- **WHEN** the stronger pre-GitOps readiness gates pass but the Sealed Secrets controller still does not become Available
- **THEN** the bootstrap MUST fail with controller-specific deployment, pod, log, and recent event diagnostics instead of only a generic rollout timeout

#### Scenario: Windows wrapper receives UTF-8 diagnostics

- **WHEN** the Windows `task-run` wrapper streams bootstrap output containing bytes outside the local code page
- **THEN** the wrapper MUST still surface readable diagnostics and the real failing phase
- **AND** the local wrapper MUST NOT terminate early with a decode exception before the bootstrap failure summary is emitted
