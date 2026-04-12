## MODIFIED Requirements

### Requirement: One-command bootstrap is a reviewed operator contract
The repository SHALL treat `task up` or its supported wrappers as a reviewed operator contract, and autonomous work affecting that path MUST pass through validation and review gates before being considered complete. When live bootstrap depends on workstation-to-Proxmox reachability, the validation ladder MUST include explicit `python scripts/haac.py check-env` evidence as a separate gate from `doctor`.

#### Scenario: Bootstrap-affecting change is closed
- **WHEN** a change touches the bootstrap path, the loop runner, or the repo operator contract
- **THEN** the loop MUST require the validation ladder and targeted review coverage described by the repo docs before closeout

#### Scenario: Live bootstrap readiness is environment-gated
- **WHEN** a bootstrap-affecting round depends on reaching the effective Proxmox access host from the operator workstation
- **THEN** the loop MUST record `python scripts/haac.py check-env` as a distinct validation result before treating `doctor`, `task -n up`, or a blocked live `task up` attempt as sufficient evidence of environment readiness
