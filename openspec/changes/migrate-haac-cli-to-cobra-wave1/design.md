## Design

### Scope

This wave closes the misleading staged wrapper behavior first and establishes the executable contract needed for the larger Python-to-Go migration.

The immediate design goals are:

- wrappers execute a repo-local `haac` binary, not `go run`;
- wrappers do not fall back to Python;
- the hidden Cobra `legacy` escape hatch is removed from the supported operator surface;
- the repo has a documented active migration plan for replacing Python-backed operator commands with native Cobra implementations.

### Binary bootstrap

The wrappers will resolve the repo-local binary path under `.tools/<os>-<arch>/bin/haac[.exe]`.

- If the binary already exists, execute it directly.
- If the binary is missing and `go` is available, build it in place with `go build`.
- If neither condition is met, fail with explicit guidance instead of silently routing through Python.

This removes the per-run compilation penalty from the steady-state `up` path while keeping first-use bootstrap recoverable.

### Command boundary

The Cobra surface must stop advertising or preserving Python as a hidden supported command path. The `legacy` command is removed, and the help text must no longer describe Python coexistence as the intended runtime contract.

### Migration posture

This change does not claim that every Python helper has already been ported to Go. It does record and start the real migration boundary:

- supported entrypoints become Cobra-only;
- the remaining Python-backed internals are treated as active migration debt and must be replaced by native Cobra commands in follow-up tasks within this same change.

### Validation

- `openspec validate migrate-haac-cli-to-cobra-wave1`
- `go test ./...`
- wrapper smoke tests for `version` and help output
- `.\haac.ps1 version` on Windows
- `sh ./haac.sh version` on Unix-like shells when available
- measure that steady-state wrapper invocations use the repo-local binary instead of `go run`
