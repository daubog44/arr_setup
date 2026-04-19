## Why

The repo now has many partial and focused validation paths, but it still lacks an explicit cold-cycle acceptance contract that proves the stack can survive a full `down` followed by `up` without manual cleanup. The operator explicitly wants that end-to-end lifecycle test recorded and repeatable.

## What Changes

- Add an explicit acceptance change for a full `task down` then `task up` lifecycle rerun.
- Add any minimal helper or reporting improvements needed to make the cold-cycle acceptance observable.
- Verify the stack again at the media and browser layers after the lifecycle run.

## Capabilities

### New Capabilities
- `full-lifecycle-acceptance`: Repo-managed cold-cycle acceptance for `down -> up -> verify`.

### Modified Capabilities
- `task-up-idempotence`: The operator contract must include the cold-cycle acceptance expectation in addition to rerun-on-partial-failure behavior.

## Impact

- Affected code may live in `Taskfile.yml`, `scripts/haac.py`, tests, and docs, but only if the cold-cycle reveals a real gap.
- Validation is the primary output of this wave: a real destructive lifecycle test plus post-bootstrap verification.
