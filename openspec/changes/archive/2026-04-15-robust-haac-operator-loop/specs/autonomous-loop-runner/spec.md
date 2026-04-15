# autonomous-loop-runner Delta

## MODIFIED Requirements

### Requirement: Repo provides an autonomous loop runner

The repository MUST provide a supported autonomous loop runner that uses the official OpenSpec CLI state, surfaces OpenSpec change-surface hygiene debt when completed or scaffold-only changes remain, creates or reuses a session worklog whose header reflects the effective session mode and selected active changes, and launches CodexPotter from a deterministic bootstrap.

#### Scenario: Active change finishes during a round

- **WHEN** the loop finishes the active change and no further actionable tasks remain in the requested scope
- **THEN** the loop SHOULD stop cleanly instead of spinning on no-op work
- **AND** if it discovers one new evidence-backed gap that is still in scope, it MAY open exactly one new change before stopping or continuing according to the round budget
