## MODIFIED Requirements

### Requirement: GitOps readiness recovery is cold-cycle safe

The staged GitOps readiness gate MUST recover repo-managed child Applications with missing hooks without immediately livelocking the same child during a cold bootstrap.

#### Scenario: Missing-hook child recycle uses a cooldown before retry

- **GIVEN** a repo-managed child Application has already been recycled once in the current `wait-for-stack` process because of a missing hook
- **WHEN** the same child briefly reports the same hook-wait state again during the parent re-sync window
- **THEN** the readiness gate MUST give the recreated child time to converge
- **AND** it MUST NOT immediately delete and recycle the same child again until the cooldown expires
