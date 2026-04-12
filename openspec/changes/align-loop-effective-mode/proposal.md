## Why

`python scripts/haac_loop.py run --mode apply --dry-run` correctly falls back to discovery when `openspec list --json` reports no active changes, but the standalone `prompt` and `worklog` helpers still emit `mode: apply`. That produces contradictory session artifacts such as `docs/worklogs/2026-04-12/1510-task-up.md` and feeds the next loop round the wrong operating contract.

## What Changes

- Align loop session artifact generation around one effective-mode resolution step before writing worklogs or rendering prompts.
- Update the standalone `prompt` and `worklog` CLI helpers so they match the same discovery fallback used by `run`.
- Add a regression check for the no-active-change apply path so future loop rounds cannot reopen the same drift.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `autonomous-loop-runner`: session prompts and worklogs must reflect the effective mode after active-change resolution, not just the requested mode

## Impact

- Affected code: `scripts/haac_loop.py`
- Affected generated artifacts: `docs/worklogs/YYYY-MM-DD/*.md`, rendered loop prompts
- Affected operator behavior: discovery rounds started from `--mode apply` with no active change now advertise the correct discovery contract everywhere
