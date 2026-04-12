## MODIFIED Requirements

### Requirement: Bootstrap phase visibility

The system MUST expose the phase structure of the bootstrap pipeline so operators can identify where a run is currently executing and where a failure occurred.

#### Scenario: Failure attribution
- **WHEN** a bootstrap phase fails
- **THEN** the operator output MUST identify the failing phase and point to the relevant command or component to inspect next
- **AND** failures caused by K3s node or CNI readiness MUST be reported as `Node configuration` failures instead of first surfacing as later GitOps rollout errors
