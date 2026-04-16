# operator-runtime-hygiene Specification

## Purpose
Define the stable operator-runtime hygiene contract for WSL bootstrap credentials and temporary artifacts so Windows runs use ephemeral `.tmp/` runtime state instead of persistent side copies or repo-root scratch files.
## Requirements
### Requirement: Windows WSL bootstrap auth uses an ephemeral runtime path

The Windows operator path MUST not rely on a persistent copy of the bootstrap SSH key in the WSL home directory.

#### Scenario: WSL Ansible bridge runs

- **WHEN** the repo launches the Ansible control path through WSL
- **THEN** the bootstrap SSH key and `known_hosts` copy MUST be materialized only under a repo-local runtime directory inside `.tmp/`
- **AND** the runtime copy MUST be removed after the run completes
- **AND** the repo-managed `known_hosts` file MAY be synchronized back from the runtime copy

### Requirement: Operator scratch artifacts stay inside `.tmp/`

The repo MUST keep operator-created scratch artifacts out of the repo root.

#### Scenario: Local investigation artifacts are created

- **WHEN** the operator or repo-local tooling creates temporary screenshots, logs, rendered manifests, or runtime dumps
- **THEN** those artifacts MUST be written under `.tmp/`
- **AND** stray legacy artifacts outside `.tmp/` MUST be cleaned up as part of repository hygiene
