## Design

### Migration posture

This is not a flag day rewrite. The migration will preserve:

- `task up`
- `.\haac.ps1 up`
- `sh ./haac.sh up`

The first wave only adds the Go/Cobra foundation and begins moving stable seams into it.

### Internal task boundary

The main Taskfile should keep only the operator-facing product path and a small set of top-level helpers. Post-install or specialized internal flows should move into subordinate Taskfiles or equivalent file-backed orchestration surfaces that are called from scripts, not by operators directly.

### Python coexistence

Python remains temporarily supported during the migration. The new Go entrypoint can shell out to existing Python behavior where needed while commands are being ported. The migration succeeds only if the resulting layout is more modular than the current state.

### Verification

- `openspec validate bootstrap-cobra-foundation`
- `python scripts/haac.py task-run -- -n up`
- `python -m py_compile scripts/haac.py scripts/haac_loop.py scripts/hydrate-authelia.py`
- build and smoke-test the Cobra CLI once introduced
