## MODIFIED Requirements

### Requirement: Windows WSL bootstrap auth uses an ephemeral runtime path
The Windows operator path MUST not rely on a persistent copy of the bootstrap SSH key in the WSL home directory.

#### Scenario: WSL Ansible bridge runs
- **WHEN** the repo launches the Ansible control path through WSL
- **THEN** the bootstrap SSH key and `known_hosts` copy MUST be materialized only under a repo-local runtime directory inside `.tmp/`
- **AND** the runtime copy MUST be removed after the run completes
- **AND** the repo-managed `known_hosts` file MAY be synchronized back from the runtime copy

#### Scenario: WSL runtime files already exist from a previous run
- **WHEN** the repo recreates the WSL runtime SSH material for a later bootstrap or verification run
- **THEN** it MUST overwrite or replace the existing runtime files idempotently
- **AND** the operator path MUST NOT fail only because the previous ephemeral file path still exists
