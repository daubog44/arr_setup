## MODIFIED Requirements

### Requirement: GitOps publication is publish-only

GitOps publication MUST not own general merge policy, but it MUST recover cleanly from publish-window remote races.

#### Scenario: local branch is behind or diverged before publication starts

- **WHEN** the operator runs the GitOps publication step while the local branch is behind or diverged from `origin/<revision>`
- **THEN** publication MUST fail with guidance to run `task sync`
- **AND** it MUST NOT auto-merge remote state as part of the publish path

#### Scenario: remote revision moves after publication starts

- **WHEN** publication has already staged or committed only generated GitOps outputs
- **AND** `origin/<revision>` moves before the final push succeeds
- **THEN** publication MUST fail with explicit recovery guidance
- **AND** it MUST NOT leave the operator with an artificial local merge-policy problem caused only by that auto-generated publication commit

### Requirement: `task sync` recovers clean fast-forwards without creating false divergence

The explicit sync path MUST remain the only merge-policy boundary while still recovering the common fast-forward-plus-dirty-worktree case safely.

#### Scenario: untracked local paths would be overwritten by the remote fast-forward

- **WHEN** the operator runs `task sync`
- **AND** local untracked paths collide with files already present in `origin/<revision>`
- **THEN** sync MUST stop before the fast-forward attempt
- **AND** it MUST report the colliding paths with explicit cleanup or move-aside guidance
