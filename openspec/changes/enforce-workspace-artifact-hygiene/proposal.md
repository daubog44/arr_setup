## Why

Live repo evidence on April 17, 2026 shows repeated local junk outside the documented artifact boundaries:

- untracked Playwright CLI snapshots under `.playwright-cli/`
- an empty `.playwright/` directory at repo root
- broken-path residue directories at repo root such as `-`, `Factory/`, `ITS/`, `Talent/`, `Tech/`, and `Microsoft/`
- the existing `task clean-artifacts` only removes older `output/` and `.tmp-falco/` leftovers, so these newer artifacts keep polluting `git status`

That violates the repo contract that temporary operator-created artifacts belong under `.tmp/` and that the workspace should stay reviewable between bootstrap rounds.

## What Changes

- Extend repo hygiene to cover current Playwright and broken-path residue artifacts.
- Make the cleanup path explicit and safe for repeated local use.
- Ignore tool-generated transient directories that should never be tracked.

## Impact

- Operators can restore a clean worktree without manual deletion rounds.
- `git status` noise from browser verification and broken absolute-path residues is reduced.
- The repo keeps a clearer distinction between tracked GitOps outputs and throwaway local artifacts.
