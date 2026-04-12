## Why

The repo has drifted back into an inconsistent OpenSpec state. `openspec list --json` shows only completed changes left under `openspec/changes/`, while `openspec/specs/` is still missing the accepted stable specs for several of those changes and `openspec status --change <name> --json` still exposes scaffold-only stubs such as `k3s-cni-runtime-idempotence` and `stabilize-k3s-cni-runtime`.

## What Changes

- Surface OpenSpec change-surface hygiene debt in the loop runner and prompt instead of treating "no active changes" as a clean idle state when completed or scaffold-only changes still exist.
- Clean the current OpenSpec surface by archiving the completed changes that have accepted delta specs and removing scaffold-only change directories that were never populated beyond `.openspec.yaml`.
- Sync the resulting stable specs and loop guidance so future rounds reason from a consistent active-versus-historical state.

## Capabilities

### New Capabilities

### Modified Capabilities

- `autonomous-loop-runner`: surface completed-change closeout debt and orphan scaffold debt in loop readiness and session context when no active change is available.

## Impact

- `scripts/haac_loop.py`
- `tests/test_haac_loop.py`
- `docs/haac-loop-prompt.md`
- `openspec/specs/`
- `openspec/changes/archive/`
- `openspec/changes/`
