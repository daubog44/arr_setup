## Why

`openspec/specs/` is no longer empty, but repo docs still describe completed changes such as `task-up-e2e-urls` as active work and the completed change history has not been cleanly archived. That leaves the operator guidance and the CLI state out of sync and makes future loop rounds reason from stale change references.

## What Changes

- Define a repo-level OpenSpec closeout capability that requires syncing accepted change specs into `openspec/specs/` and archiving completed changes out of the active change set.
- Sync the accepted capability requirements from the three completed changes into stable specs under `openspec/specs/`.
- Archive the completed changes under `openspec/changes/archive/` after their stable specs are in place.
- Update repo docs and loop prompts so they reference stable specs or archived history instead of treating completed changes as active.

## Capabilities

### New Capabilities
- `openspec-change-archival`: stable-spec sync and archive rules for completed OpenSpec changes in this repo

### Modified Capabilities

- None.

## Impact

- Affected spec surfaces: `openspec/specs/`, `openspec/changes/archive/`
- Affected completed change history: `openspec/changes/task-up-e2e-urls/`, `openspec/changes/haac-autonomous-loop/`, `openspec/changes/haac-general-gap-discovery/`
- Affected loop and operator docs: `README.md`, `docs/haac-loop-prompt.md`, related loop docs that mention active changes
