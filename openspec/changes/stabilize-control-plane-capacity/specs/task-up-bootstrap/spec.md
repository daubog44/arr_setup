## ADDED Requirements

### Requirement: K3s master memory must be `.env`-driven

The bootstrap path MUST derive K3s master memory sizing from the central operator environment instead of a Terraform hardcoded literal.

#### Scenario: Operator changes master memory in `.env`

- **WHEN** the operator updates the master memory input in `.env`
- **THEN** the OpenTofu environment mapping MUST expose it as a `TF_VAR_*` input
- **AND** the K3s master module MUST use that value during reconciliation

#### Scenario: Example configuration is reviewed

- **WHEN** an operator inspects `.env.example`
- **THEN** the master memory input MUST be documented there
- **AND** changing control-plane memory MUST not require editing Terraform source

#### Scenario: Bootstrap continues after the master container is recreated

- **GIVEN** a `task up` run changes the K3s master memory and OpenTofu replaces the master container
- **WHEN** the bootstrap path enters the Ansible configuration phase
- **THEN** the repo-managed SSH trust store MUST refresh the K3s node host keys before Ansible connects
- **AND** the rerun path MUST not require a manual `known_hosts` cleanup to continue
- **AND** the recreated node baseline MUST refresh package metadata before the first required apt install so `configure-os` does not fail on stale package indexes
- **AND** workers that still carry the previous control-plane token or CA trust MUST be reset and rejoined instead of looping indefinitely against the replaced master
