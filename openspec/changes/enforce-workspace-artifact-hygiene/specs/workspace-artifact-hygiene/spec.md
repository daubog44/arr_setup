## ADDED Requirements

### Requirement: Cleanup removes current non-contract local artifact directories

The workspace cleanup surface MUST remove the known local artifact directories that are outside `.tmp/` and tracked GitOps outputs.

#### Scenario: operator runs the cleanup task after browser verification and local tooling sessions

- **WHEN** the operator runs `task clean-artifacts`
- **THEN** the cleanup path MUST remove transient Playwright directories created at repo root
- **AND** it MUST remove the known broken-path residue directories observed at repo root
- **AND** it MUST leave tracked repo content untouched

### Requirement: Transient browser artifacts stay ignored

Transient browser automation artifacts MUST NOT appear as candidate tracked content.

#### Scenario: Playwright CLI writes local capture state

- **WHEN** Playwright CLI creates `.playwright-cli/` or `.playwright/` content in the workspace
- **THEN** those paths MUST be ignored by Git
- **AND** operators MUST still be able to remove them through the documented cleanup task
