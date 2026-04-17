## Why

The Windows bootstrap wrapper currently streams `task` output using the workstation code page instead of a stable UTF-8 contract. Live evidence on April 17, 2026 reproduced `UnicodeDecodeError: 'charmap' codec can't decode byte 0x8f` while `python scripts/haac.py task-run -- up` was surfacing Ansible/K3s diagnostics, which masked the real cluster failure and broke the `task up` operator path.

## What Changes

- Force UTF-8-with-replacement decoding when `scripts/haac.py` streams `task` output to the operator.
- Preserve the existing line-by-line phase tracking and failure summaries while making the stream resilient to non-CP1252 bytes.
- Add focused regression coverage for the Windows streaming path.

## Capabilities

### New Capabilities
- `windows-task-output-streaming`: the repo-managed Windows bootstrap wrapper can stream UTF-8 task output without crashing on locale-specific decode errors.

### Modified Capabilities
- `task-up-bootstrap`: bootstrap failure reporting on Windows must remain readable instead of crashing in the local wrapper before the real failing phase is surfaced.

## Impact

- Affected code lives in `scripts/haac.py` and `tests/test_haac.py`.
- This changes the local operator/runtime behavior on Windows without changing the supported product surface (`task up` and wrappers).
