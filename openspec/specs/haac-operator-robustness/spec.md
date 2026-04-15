# haac-operator-robustness Specification

## Purpose
TBD - created by archiving change robust-haac-operator-loop. Update Purpose after archive.
## Requirements
### Requirement: One-command bootstrap remains the product surface

The repository MUST continue to treat `task up` and its platform wrappers as the only supported operator bootstrap path while robustness work is ongoing.

#### Scenario: Internal refactors happen

- **WHEN** orchestration logic is moved, split, or hardened
- **THEN** the supported operator contract MUST remain `task up`, `.\haac.ps1 up`, and `sh ./haac.sh up`
- **AND** the phase visibility and recovery expectations of that path MUST not regress

### Requirement: Official UI auth stays edge-governed

All official browser-facing UIs MUST remain governed by one shared edge-auth model unless a route is explicitly declared public.

#### Scenario: Official protected UI is published

- **WHEN** an official UI route is enabled
- **THEN** it MUST be protected by the shared Authelia edge-auth contract or an explicitly documented equivalent
- **AND** Homepage plus endpoint verification MUST classify that route as protected

### Requirement: Robustness debt stays evidence-backed

The autonomous hardening loop MUST keep remaining robustness work tied to evidence instead of ad hoc cleanup.

#### Scenario: Another robustness gap appears

- **WHEN** validation, runtime checks, or review expose a new reproducible gap in bootstrap, GitOps, auth, routing, secrets, or loop behavior
- **THEN** the repo MUST track that work through an evidence-backed OpenSpec change or task update
- **AND** the loop MUST not silently treat the repo as fully done while actionable robustness debt remains in scope

