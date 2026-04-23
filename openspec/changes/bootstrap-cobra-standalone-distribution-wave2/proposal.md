## Why

The current Cobra surface still assumes an already-cloned repo, repo-local wrappers, and Task as the practical operator boundary. That blocks the product shape the operator now wants: a versioned `haac` binary that can initialize a workspace from Git, validate `.env`, install or update dependencies, and then run the homelab normally.

## What Changes

- Introduce a standalone Cobra distribution and workspace bootstrap flow centered on `haac init`.
- Add CLI-managed tool installation and update flows with explicit workspace targeting and local versus global scope.
- Publish versioned `haac` binaries as release artifacts with checksums instead of relying only on repo-local `go build`.
- Update the documented operator contract so direct `haac up` / `haac down` from an initialized workspace become first-class entrypoints.

## Capabilities

### New Capabilities
- `operator-cli-distribution`: a standalone `haac` binary can initialize a workspace from Git, seed the required `.env` scaffold, and manage the operator toolchain lifecycle.

### Modified Capabilities
- `task-up-bootstrap`: the single-command bootstrap contract expands to direct `haac up` / `haac down` from an initialized workspace while preserving the same phase and rerun guarantees.
- `bootstrap-boundaries`: wrappers and Task remain compatibility shims, but the stable product surface becomes the standalone Cobra binary without Python fallback semantics.

## Impact

- Affected code lives primarily under `cmd/haac/`, `internal/cli/`, `haac.ps1`, `haac.sh`, repo docs, and release metadata under `.github/` plus `.goreleaser.yaml`.
- This change affects operator onboarding, local tool bootstrap, release/versioning, and the documented bootstrap entrypoints for the whole homelab product.
