## Why

`task up` is the primary product contract of this repo, but the current stable bootstrap spec mostly defines the happy-path phases and final URL output. It does not yet define rerun-safe behavior for partial or converged environments, which leaves repeated runs vulnerable to duplicate side effects, ambiguous recovery, and manual cleanup after mid-pipeline failures.

## What Changes

- Define a stable idempotence capability for `task up` that covers rerun safety across preflight, OpenTofu, Ansible, GitOps bootstrap, Cloudflare reconciliation, and verification.
- Require `task up` to treat reruns as reconciliation against real system state instead of assuming a first-run bootstrap.
- Require deterministic phase-specific failure and recovery reporting so operators know whether a full rerun is safe.
- Add verification expectations for repeated runs, including no-op or convergent behavior when the environment is already aligned.

## Capabilities

### New Capabilities
- `task-up-idempotence`: rerun-safe, convergent, and phase-aware behavior for the one-command bootstrap path

### Modified Capabilities
- `task-up-bootstrap`: tighten the stable bootstrap contract so startup correctness and final reporting remain consistent when idempotence guards are added

## Impact

- Affected bootstrap entrypoints: `Taskfile.yml`, `haac.ps1`, `haac.sh`
- Affected orchestration logic: `scripts/haac.py`
- Affected operator and loop guidance: `README.md`, `AGENTS.md`, `docs/runbooks/task-up.md`, loop docs where `task up` is the primary contract
- Affected validation surface: `task -n up`, `task up`, repeated `task up` runs, and the autonomous loop verification ladder
