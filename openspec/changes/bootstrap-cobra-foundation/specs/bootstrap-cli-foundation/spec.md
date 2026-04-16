## ADDED Requirements

### Requirement: Operator contract survives the Cobra migration
The repository MUST preserve the documented operator entrypoints while the implementation migrates toward a Go/Cobra foundation.

#### Scenario: Operator runs the supported entrypoints
- **WHEN** the operator invokes `task up`, `.\haac.ps1 up`, or `sh ./haac.sh up`
- **THEN** the documented contract MUST remain stable during the migration
- **AND** the repo MUST be free to route those entrypoints through a Cobra-based implementation layer internally

### Requirement: Migration is incremental and modular
The repo MUST be able to move commands from Python into Go incrementally instead of requiring a big-bang rewrite.

#### Scenario: A command is not yet ported
- **WHEN** a supported operator command has not yet been ported into the Cobra implementation
- **THEN** the repo MAY delegate that command to the existing implementation
- **AND** the migration boundary MUST remain explicit and reviewable
