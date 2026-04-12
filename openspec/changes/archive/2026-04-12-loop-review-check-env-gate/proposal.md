## Why

The loop's bootstrap review ladder still treats `doctor` as the first environment-level gate, but repeated live acceptance attempts proved that `doctor` passing does not mean `task up` can actually start from this workstation. `python scripts/haac.py check-env` is the gate that validates the effective Proxmox access host before sync or provisioning, so omitting it leaves a real bootstrap blind spot in loop closeout.

## What Changes

- Add `python scripts/haac.py check-env` to the documented bootstrap validation ladder before `doctor` and before any live `task up` attempt.
- Align the repo-local loop review skill and related loop guidance so bootstrap-affecting rounds treat `check-env` as the explicit live-environment gate, distinct from tool installation checks.
- Update the session worklog guidance to record `check-env` results when a live bootstrap run is blocked before remote phases begin.

## Capabilities

### New Capabilities

### Modified Capabilities

- `loop-self-improvement`: bootstrap-affecting closeout must require the explicit `check-env` preflight gate when live workstation-to-Proxmox reachability determines whether `task up` can run.

## Impact

- `docs/loop-review.md`
- `docs/haac-loop-prompt.md`
- `docs/loop-worklog.md`
- `.codex/skills/haac-loop-review/SKILL.md`
- `openspec/specs/loop-self-improvement/spec.md`
