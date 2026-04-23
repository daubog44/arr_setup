## MODIFIED Requirements

### Requirement: Wrapper entrypoints preserve the supported Cobra contract

Wrapper entrypoints MUST preserve the supported direct-CLI semantics without reintroducing a staged Python fallback.

#### Scenario: operator uses the standalone binary

- **WHEN** an operator runs `haac` directly from an initialized workspace or an installed global binary
- **THEN** that direct binary MUST be treated as the primary supported operator surface

#### Scenario: operator uses a compatibility shim

- **WHEN** an operator runs `.\haac.ps1 <args>`, `sh ./haac.sh <args>`, or `task <target>`
- **THEN** the shim MUST preserve the supported Cobra semantics for public commands
- **AND** it MUST NOT treat Python fallback as part of the stable product boundary
