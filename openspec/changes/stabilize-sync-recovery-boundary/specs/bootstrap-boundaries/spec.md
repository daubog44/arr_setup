## MODIFIED Requirements

### Requirement: `task up` does not own Git merge policy

The main bootstrap path MUST not perform remote merge policy implicitly.

#### Scenario: default bootstrap preflight runs

- **WHEN** the operator runs `task up`
- **THEN** the default preflight path MUST validate local prerequisites without invoking the explicit Git merge workflow
- **AND** any required merge policy MUST remain in the explicit `task sync` path

### Requirement: GitOps publication is publish-only

GitOps publication MUST not auto-merge remote state.

#### Scenario: local branch is behind or diverged

- **WHEN** the operator runs the GitOps publication step while the local branch is behind or diverged from `origin/<revision>`
- **THEN** publication MUST fail with guidance to run `task sync`
- **AND** it MUST NOT auto-merge remote state as part of the publish path

### Requirement: Low-level Git state helpers live outside the main orchestrator

The main orchestration file MUST not own low-level Git state inspection directly.

#### Scenario: bootstrap code needs Git ref state

- **WHEN** the bootstrap path checks repo dirtiness, remote existence, or ref relationships
- **THEN** the low-level helper logic MUST live in `scripts/haaclib/`
- **AND** `scripts/haac.py` MUST keep orchestration and operator-facing policy only

### Requirement: Internal bootstrap subtasks live outside the main Taskfile

The main Taskfile MUST keep internal GitOps and post-install orchestration thin.

#### Scenario: internal bootstrap helpers are needed

- **WHEN** `task up` or a related operator-facing task needs lower-level helpers for GitOps publication, ArgoCD waiting, public verification, or post-install repair
- **THEN** the implementation of those helpers MUST live in a subordinate internal task file or equivalent file-backed orchestration surface
- **AND** the main `Taskfile.yml` MAY keep only thin compatibility stubs that delegate into that internal boundary

### Requirement: Wrapper entrypoints preserve the staged CLI seam

Wrapper entrypoints MUST preserve the existing task argument contract while the Cobra migration is in progress.

#### Scenario: operator uses a shell wrapper

- **WHEN** an operator runs `.\haac.ps1 <args>` or `sh ./haac.sh <args>`
- **THEN** the wrapper MUST preserve the existing `task` argument semantics
- **AND** global Task flags such as `-n` MUST survive the staged Go/Cobra bridge unchanged
- **AND** it MUST be allowed to prefer the repo-local Go/Cobra entrypoint when available while keeping a Python fallback until the migration is complete

### Requirement: `task sync` recovers clean fast-forwards without creating false divergence

The explicit sync path MUST remain the only merge-policy boundary while still recovering the common fast-forward-plus-dirty-worktree case safely.

#### Scenario: remote revision is ahead and local worktree is dirty

- **WHEN** the operator runs `task sync`
- **AND** the configured remote revision is ahead of local `HEAD`
- **AND** local tracked worktree changes are present
- **THEN** sync MUST update the branch to the remote revision before checkpointing recovered local changes
- **AND** it MUST NOT create a local checkpoint that turns a clean fast-forward into divergence
