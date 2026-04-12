# loop-self-improvement Specification

## Purpose
Define how the autonomous loop opens evidence-backed changes and enforces review for bootstrap-affecting work.
## Requirements
### Requirement: One-command bootstrap is a reviewed operator contract
The repository SHALL treat `task up` or its supported wrappers as a reviewed operator contract, and autonomous work affecting that path MUST pass through validation and review gates before being considered complete. When live bootstrap depends on workstation-to-Proxmox reachability, the validation ladder MUST include explicit `python scripts/haac.py check-env` evidence as a separate gate from `doctor`.

#### Scenario: Bootstrap-affecting change is closed
- **WHEN** a change touches the bootstrap path, the loop runner, or the repo operator contract
- **THEN** the loop MUST require the validation ladder and targeted review coverage described by the repo docs before closeout

#### Scenario: Live bootstrap readiness is environment-gated
- **WHEN** a bootstrap-affecting round depends on reaching the effective Proxmox access host from the operator workstation
- **THEN** the loop MUST record `python scripts/haac.py check-env` as a distinct validation result before treating `doctor`, `task -n up`, or a blocked live `task up` attempt as sufficient evidence of environment readiness

### Requirement: Loop can create a new evidence-backed change for missing capabilities
The autonomous loop MUST be able to open exactly one new OpenSpec change when the repo, the broader HaaC stack, or the loop itself is missing a required capability and the evidence meets the discovery policy.

#### Scenario: Missing loop capability discovered
- **WHEN** the loop finds a real missing capability in preflight, validation, review, discovery, or bootstrap behavior
- **THEN** it MUST create one narrow evidence-backed OpenSpec change instead of silently working around the issue

#### Scenario: Missing HaaC capability discovered
- **WHEN** the loop finds a real evidence-backed gap in infrastructure, GitOps, security, storage, networking, automation, DRY, or operator parity
- **THEN** it MUST be allowed to create one narrow OpenSpec change that includes the proposed minimal solution

#### Scenario: Evidence is weak
- **WHEN** the loop does not have a failing command, concrete mismatch, or missing contract
- **THEN** it MUST NOT create a new OpenSpec change

