## Context

The repo deliberately keeps `.env` as the single source of truth for bootstrap inputs. Password handling is already modeled that way for the main operator path: `Taskfile.yml` reads `LXC_PASSWORD` once and exports it as both `LXC_PASSWORD` and `PROXMOX_HOST_PASSWORD` before calling `scripts/haac.py`.

The gap is that `scripts/haac.py` itself still merged `.env` values literally, so any supporting command that relied on `merged_env()` without coming through Task saw `LXC_PASSWORD` but not `PROXMOX_HOST_PASSWORD`. That leaves the orchestration layer internally inconsistent with its own documented input contract.

## Goals / Non-Goals

**Goals:**

- Keep `LXC_PASSWORD` as the declared `.env` password input.
- Let `scripts/haac.py` derive `PROXMOX_HOST_PASSWORD` automatically when the caller did not set one.
- Preserve explicit `PROXMOX_HOST_PASSWORD` overrides for environments that need different credentials.
- Add low-cost regression coverage at the Python layer instead of relying on live bootstrap failures to detect drift.

**Non-Goals:**

- This change does not redesign Proxmox authentication.
- This change does not add another required `.env` field.
- This change does not remove the existing Taskfile exports; it makes the orchestration layer correct even when those exports are not the caller.

## Decisions

### Centralize the fallback in `merged_env()`

`merged_env()` is already the common entrypoint for `.env` plus process environment resolution. It is the narrowest place to preserve the documented source-of-truth rule without scattering special cases across `run_ansible`, helper commands, or validation code.

Alternative considered: patch only `run_ansible_wsl()` and the specific direct callers that need Proxmox host auth. Rejected because the same hidden split could reappear in other helpers that depend on `merged_env()`.

### Preserve explicit override precedence

The fallback only applies when `PROXMOX_HOST_PASSWORD` is absent or empty. If an operator or wrapper sets a different host password explicitly, that value remains authoritative.

Alternative considered: always copy `LXC_PASSWORD` into `PROXMOX_HOST_PASSWORD`. Rejected because it would block legitimate override use cases.

### Cover the behavior with stdlib `unittest`

The repo already uses stdlib-based tests for local loop behavior. A focused `tests/test_haac.py` module can patch `load_env_file()` and `os.environ` to verify both fallback and explicit override behavior without introducing new dependencies or touching the real `.env`.

## Risks / Trade-offs

- [Direct import tests can accidentally depend on the real environment] -> patch `load_env_file()` and isolate `os.environ` inside the test case.
- [Docs could overexplain an internal detail] -> document only the operator-relevant rule: `LXC_PASSWORD` remains the source of truth unless `PROXMOX_HOST_PASSWORD` is explicitly overridden by the caller.
- [Taskfile and Python behavior could drift again later] -> keep the spec and regression test focused on the fallback contract, not just the current implementation.

## Migration Plan

1. Formalize the modified `task-up-bootstrap` requirement for password-source reuse.
2. Keep the local `merged_env()` fallback implementation and add regression tests.
3. Update the bootstrap docs to state the override/fallback rule clearly.
4. Run the bootstrap validation ladder that is safe in the current environment.

## Open Questions

- None. The change is intentionally narrow and backward compatible.
