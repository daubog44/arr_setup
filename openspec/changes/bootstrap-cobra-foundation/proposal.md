## Why

`scripts/haac.py` remains the main bootstrap brain and has grown into a very large monolith. The repo has already started extracting helpers into `scripts/haaclib/`, but the operator path is still Python-first and Taskfile entries point straight at the monolith. To improve maintainability without breaking `task up`, the repo needs a staged Go/Cobra foundation and clearer internal task boundaries.

## What Changes

- Introduce a repo-managed Go/Cobra bootstrap foundation that can gradually absorb operator commands without breaking the existing entrypoints.
- Keep `task up`, `haac.ps1`, and `haac.sh` stable while beginning the migration away from direct Taskfile-to-Python coupling.
- Add subordinate internal task files for post-install or maintenance flows so the main Taskfile stays thin.
- Continue extracting orchestration logic into focused modules instead of letting a single script grow indefinitely.

## Capabilities

### New Capabilities
- `bootstrap-cli-foundation`: staged Go/Cobra foundation that preserves the operator contract while enabling incremental migration from the Python monolith.

### Modified Capabilities
- `bootstrap-boundaries`: internal post-install and maintenance task orchestration must stay modular and out of the main Taskfile surface.

## Impact

- Affected areas include `Taskfile.yml`, `scripts/`, possible new `cmd/` or `internal/` Go paths, and wrapper entrypoints.
- This change is structural and compatibility-focused rather than a product-surface change.
