## Why

The explicit `task sync` path is supposed to be the recovery boundary when GitOps publication is blocked by a remote fast-forward. Live evidence on April 17, 2026 showed a failure mode where the repo had regenerated tracked GitOps outputs locally, `origin/main` had advanced by one safe CI commit, and the current sync logic would checkpoint first and only then compare refs, turning a simple fast-forward into an artificial divergence.

## What Changes

- Make the explicit sync path handle the common "remote ahead + local generated changes" case without creating false divergence.
- Preserve publish-only behavior for `task up` and `push-changes`; merge policy remains explicit in `task sync`.
- Add regression coverage for the sync decision path and the behind-plus-dirty recovery flow.
- Record the safer sync boundary in the stable bootstrap contract.

## Capabilities

### New Capabilities

- `sync-recovery-boundary`: the explicit sync path can safely fast-forward and preserve local generated changes without forcing manual conflict handling when the remote only moved ahead cleanly.

### Modified Capabilities

- `bootstrap-boundaries`: the sync boundary requirement changes to cover behind-plus-dirty recovery without moving merge policy back into `task up`.

## Impact

- Affected code lives in `scripts/haac.py`, `scripts/haaclib/gitstate.py`, and `tests/test_haac.py`.
- The stable spec change lives under `openspec/specs/bootstrap-boundaries/`.
- This changes local operator recovery behavior on the Git boundary but does not change the supported product entrypoints.
