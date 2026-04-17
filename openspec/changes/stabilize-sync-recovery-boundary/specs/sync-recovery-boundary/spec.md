## ADDED Requirements

### Requirement: Explicit sync can recover from a clean remote fast-forward while local generated state is dirty
The explicit sync path MUST preserve local dirty worktree state when the configured remote revision is ahead and the branch relationship is still a clean fast-forward.

#### Scenario: Remote revision is ahead and local worktree is dirty
- **WHEN** the operator runs `task sync`
- **AND** `origin/<revision>` is ahead of local `HEAD`
- **AND** local tracked worktree changes are present
- **THEN** the sync path MUST fast-forward to `origin/<revision>` without manufacturing branch divergence
- **AND** it MUST restore the local worktree changes after the fast-forward
- **AND** it MUST leave the repo in a state where a subsequent publish-only GitOps commit can proceed

### Requirement: Explicit sync fails closed on restore conflicts
The explicit sync path MUST not silently lose or overwrite local worktree changes if replaying them after a fast-forward produces conflicts.

#### Scenario: Re-applying local changes conflicts after fast-forward
- **WHEN** the explicit sync path restores previously preserved local changes after updating to `origin/<revision>`
- **AND** Git reports a conflict while restoring those changes
- **THEN** sync MUST fail with an explicit recovery message
- **AND** it MUST NOT continue into automatic publication
