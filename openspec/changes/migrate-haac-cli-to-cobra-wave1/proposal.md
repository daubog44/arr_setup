## Why

The current Go/Cobra surface is only a staged shim and does not satisfy the supported operator contract as a true replacement for the Python CLI.

Concrete evidence in the repo today:

- [haac.ps1](C:\Users\Utente\OneDrive - ITS Tech Talent Factory\Desktop\dev\arr_setup-main\haac.ps1) still runs `go run ./cmd/haac` on every invocation and falls back to `scripts/haac.py` when the Go path fails.
- [haac.sh](C:\Users\Utente\OneDrive - ITS Tech Talent Factory\Desktop\dev\arr_setup-main\haac.sh) has the same Python fallback.
- [internal/cli/root.go](C:\Users\Utente\OneDrive - ITS Tech Talent Factory\Desktop\dev\arr_setup-main\internal\cli\root.go) still exposes a hidden `legacy` command that runs the Python CLI directly.
- [Taskfile.yml](C:\Users\Utente\OneDrive - ITS Tech Talent Factory\Desktop\dev\arr_setup-main\Taskfile.yml) and [Taskfile.internal.yml](C:\Users\Utente\OneDrive - ITS Tech Talent Factory\Desktop\dev\arr_setup-main\Taskfile.internal.yml) call `scripts/haac.py` across the supported operator path.

This matters because:

- the wrapper startup path recompiles Cobra every time, which adds avoidable latency before `up` even starts;
- the supported operator contract still depends on Python as the real command surface;
- the current Cobra posture is misleading because it looks like a migration but still preserves Python as the hidden source of truth.

## What Changes

- remove wrapper-level Python fallback from the supported `haac` entrypoints;
- stop using `go run` as the steady-state entrypoint and prefer a repo-local built `haac` binary;
- begin replacing the Python CLI command surface with native Cobra subcommands for the supported operator path;
- update the bootstrap docs and contracts so they describe the real Cobra-first operator surface instead of the staged bridge.

## Capabilities

### New Capabilities

- `operator-cli-surface`: the supported `haac` operator surface is owned by a repo-local Cobra CLI without Python fallback.

### Modified Capabilities

- `task-up-bootstrap`: wrapper entrypoints and the supported bootstrap path must describe and use the same Cobra-first contract.
- `bootstrap-boundaries`: the staged Python fallback is no longer part of the supported wrapper boundary once this migration completes.

## Impact

- Affected areas include [haac.ps1](C:\Users\Utente\OneDrive - ITS Tech Talent Factory\Desktop\dev\arr_setup-main\haac.ps1), [haac.sh](C:\Users\Utente\OneDrive - ITS Tech Talent Factory\Desktop\dev\arr_setup-main\haac.sh), [cmd/haac/main.go](C:\Users\Utente\OneDrive - ITS Tech Talent Factory\Desktop\dev\arr_setup-main\cmd\haac\main.go), [internal/cli](C:\Users\Utente\OneDrive - ITS Tech Talent Factory\Desktop\dev\arr_setup-main\internal\cli), Taskfiles, and the operator docs.
- The migration is bootstrap-critical because it changes the supported entrypoints for `up`, `down`, preflight, and tool installation.
