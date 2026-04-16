# bootstrap-boundaries Specification

## Purpose
Define the stable contract that keeps `task up` publish-only on the Git boundary, moves merge policy into the explicit `task sync` path, and keeps low-level Git state helpers out of the main orchestration file.
## Requirements
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
