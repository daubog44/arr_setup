## MODIFIED Requirements

### Requirement: Completed or superseded bootstrap changes move out of the active change set

The repository MUST archive bootstrap changes that are no longer the live source of pending work once their accepted requirements are represented in stable specs.

#### Scenario: In-progress change is superseded by accepted stable behavior

- **WHEN** a bootstrap change still appears in `openspec list` but the accepted behavior is already implemented and synced into stable specs
- **THEN** that change MUST be archived instead of remaining in the active backlog
- **AND** the remaining active change set MUST reflect only unresolved observable outcomes
