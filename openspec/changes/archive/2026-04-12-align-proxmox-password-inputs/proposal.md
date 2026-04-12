## Why

The documented bootstrap input surface still treats `LXC_PASSWORD` as the single password source of truth:

- `.env.example` defines `LXC_PASSWORD`
- `README.md` and `docs/runbooks/task-up.md` list `LXC_PASSWORD` in the required input set
- `cmd_check_env()` requires `LXC_PASSWORD` but not `PROXMOX_HOST_PASSWORD`

The runtime path is not fully aligned with that contract yet. Ansible inventory still looks up `PROXMOX_HOST_PASSWORD`, and `scripts/haac.py` exports that variable to WSL only if it already exists in the merged environment. The current `Taskfile.yml` masks the gap by copying `LXC_PASSWORD` into `PROXMOX_HOST_PASSWORD` for `task up`, `configure-os`, and `provision-infra`, but direct orchestration entrypoints still depend on an undocumented duplicate variable.

Concrete evidence:

- `ansible/inventory.yml` and `tofu/inventory.tftpl` read `lookup('env', 'PROXMOX_HOST_PASSWORD')`
- `Taskfile.yml` lines 72-73, 96-97, and 105-106 export both `PROXMOX_HOST_PASSWORD` and `LXC_PASSWORD`
- synthetic reproduction against `HEAD:scripts/haac.py` with only `LXC_PASSWORD=demo-secret` returns `HEAD_PROXMOX_HOST_PASSWORD=None`

That mismatch matters because `scripts/haac.py` is the bootstrap orchestration layer. Supporting commands should not require a second password input that the operator contract does not declare.

## What Changes

- Derive `PROXMOX_HOST_PASSWORD` from `LXC_PASSWORD` inside `scripts/haac.py` when no explicit host password is present, while preserving explicit override behavior.
- Add regression coverage for the merged-env fallback so future refactors cannot reintroduce the hidden split.
- Align the operator docs and stable bootstrap spec with the password source-of-truth rule used by supporting orchestration commands.

## Capabilities

### Modified Capabilities

- `task-up-bootstrap`: supporting bootstrap orchestration commands reuse the documented `LXC_PASSWORD` input unless the caller explicitly overrides `PROXMOX_HOST_PASSWORD`.

## Impact

- Affected orchestration logic: `scripts/haac.py`
- Affected validation surface: `python scripts/haac.py check-env`, `python scripts/haac.py doctor`, `python scripts/haac.py task-run -- -n up`, Python regression tests
- Affected operator guidance: `README.md`, `docs/runbooks/task-up.md`
