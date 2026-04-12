## Why

The loop runner still keys new worklog files to the current minute, so repeated `task-up` discovery or apply helpers can fragment one session across multiple same-day files. That breaks the prompt contract around the "current session worklog" and makes later rounds read or update the wrong diary.

## What Changes

- Reuse the current same-day worklog for repeated loop `run`, `prompt`, and `worklog` invocations that target the same slug.
- Preserve the existing header-sync behavior when a matching worklog is reused.
- Add regression coverage for same-day worklog reuse and for first-run file creation when no matching worklog exists.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `autonomous-loop-runner`: repeated loop helpers for the same slug must keep using one current session worklog instead of minting a new minute-stamped file every time

## Impact

- Affected code: `scripts/haac_loop.py`
- Affected tests: `tests/test_haac_loop.py`
- Affected generated artifacts: `docs/worklogs/YYYY-MM-DD/*.md`
