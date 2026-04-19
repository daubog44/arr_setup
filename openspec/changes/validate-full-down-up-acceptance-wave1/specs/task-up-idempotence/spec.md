## MODIFIED Requirements

### Requirement: Task-up lifecycle verification includes destructive acceptance

The bootstrap contract MUST describe the existence of a destructive lifecycle validation path in addition to partial-failure reruns.

#### Scenario: The operator asks whether the stack survives a full rebuild

- **WHEN** the repo documents bootstrap validation
- **THEN** it MUST describe the supported `down -> up -> verify` acceptance surface
- **AND** it MUST keep `task up` as the supported recovery path after the destructive cycle unless a failure explicitly requires manual intervention

