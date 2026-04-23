## Context

The current repo already has a Cobra binary and wrapper-owned `up` / `down`, but the operator experience still starts with a Git clone plus wrapper scripts in the repo root. Tool bootstrap is repo-local and useful, yet it is still tied to "I am already inside the repo", and there is no release artifact pipeline that turns the Cobra binary into the product-distributed entrypoint.

The user now wants a different boundary:

- download a versioned `haac` binary;
- run `haac init` to clone the HaaC workspace from Git;
- fill only `.env`;
- use `haac install-tools`, `haac update-tools`, `haac up`, and `haac down` directly.

That requires a workspace-aware Cobra surface, a release pipeline, and an explicit separation between the standalone binary and the initialized workspace it operates on.

## Goals / Non-Goals

**Goals:**
- Make the standalone Cobra binary a first-class operator surface, not just a repo-local shim.
- Add `haac init` so a user can bootstrap a fresh workspace from Git without manually cloning first.
- Add explicit `install-tools` and `update-tools` flows that can target either a workspace-local portable toolchain or a user-global install location.
- Add version metadata and versioned release artifacts for `haac`.
- Update docs so the product contract describes the direct binary first and wrappers second.

**Non-Goals:**
- Fully remove Taskfiles in this wave.
- Fully rewrite every remaining Python-backed internal helper in this wave.
- Support non-Git storage backends in this wave; the design should leave room for them later.
- Add unattended self-update over the network in this wave.

## Decisions

### Workspace resolution becomes explicit

`haac init` must work outside an existing repo, while most other commands still operate on an initialized workspace. The CLI will therefore separate:

- commands that need no existing workspace (`init`, `version`);
- commands that operate on a workspace selected by `--workspace` or discovered from the current directory.

Alternative considered: keep the current implicit repo-root-only discovery everywhere. Rejected because it cannot support a standalone binary that initializes new workspaces.

### `haac init` is Git-first

The initial standalone bootstrap path will use `git clone` against the configured repository URL and optional revision/branch, then seed `.env` from `.env.example` when needed.

Alternative considered: embed the full repo contents directly into the binary. Rejected for this wave because it would bloat the binary, complicate updates, and still not solve the future "other storage backends" problem cleanly.

### Tool lifecycle is scope-aware

The CLI will support:

- `--scope local`: install portable tools into the initialized workspace under `.tools/`;
- `--scope global`: install portable binaries into a user-level global bin directory.

`update-tools` will reuse the same installer codepath but force refresh against the configured versions instead of silently accepting the current marker.

Alternative considered: keep only repo-local installs. Rejected because the requested product boundary explicitly wants a globally usable binary and optional global tool bootstrap.

### Release distribution uses GoReleaser plus GitHub Actions

The repo will publish tagged `haac` artifacts through a release workflow and a checked-in `.goreleaser.yaml`, with version metadata wired into the binary at build time.

Alternative considered: maintain ad hoc `go build` scripts or only GitHub Actions upload-artifact output. Rejected because the user asked for versioned artifacts as a product surface, and GoReleaser gives predictable archive naming and checksums with less repo-specific glue.

### Wrappers remain compatibility shims

`haac.ps1`, `haac.sh`, and `task` stay in the repo for compatibility, but docs and specs will describe them as convenience shims around the standalone Cobra product boundary instead of the product boundary itself.

Alternative considered: delete wrappers and Task immediately. Rejected because existing operators still rely on them and the backend orchestration is not yet fully detached from the repo.

## Risks / Trade-offs

- [Global install PATH drift] -> The CLI can install binaries into a user-global directory, but the operator may still need to add that directory to PATH manually; docs must make that explicit.
- [Git-only init] -> `haac init` will still require `git` and network access; later storage backends need a fetcher abstraction instead of special-casing more clone logic.
- [Release workflow confidence] -> GitHub release publishing cannot be fully proven live from this local session; mitigate by keeping the configuration minimal and validating the local build/version path.
- [Remaining internal Python debt] -> The product boundary becomes Cobra-first, but some internal bootstrap implementation still remains outside Go; docs and specs must not overclaim full backend removal.

## Migration Plan

1. Add the OpenSpec contract for standalone Cobra distribution and direct `haac up` / `haac down`.
2. Implement workspace-aware Cobra commands for `init`, `install-tools`, and `update-tools`.
3. Add binary version metadata plus versioned release packaging.
4. Update docs to describe the direct binary flow first.
5. Validate the new local flows (`init`, `install-tools`, `update-tools`, `version`) and confirm the existing bootstrap surface still passes dry-run and live wrapper/Cobra checks.

Rollback is straightforward: revert the new command surface and release metadata while keeping the already-working repo-local wrapper path.

## Open Questions

- Which non-Git storage backend should be the first follow-up after the Git-first `init` path?
- Should global control-node package installation grow platform-specific package-manager support beyond the current Windows+WSL path in the next wave, or should the next wave prioritize removing more Python/Task internals first?
