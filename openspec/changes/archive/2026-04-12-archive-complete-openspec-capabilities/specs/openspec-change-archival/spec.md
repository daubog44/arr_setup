## ADDED Requirements

### Requirement: Completed changes sync accepted capabilities into stable specs
The repository MUST sync the accepted requirements from a completed OpenSpec change into `openspec/specs/<capability>/spec.md` before the change is treated as closed history.

#### Scenario: Completed change with accepted delta specs
- **WHEN** an OpenSpec change is complete and its accepted requirements exist only inside `openspec/changes/<change>/specs/`
- **THEN** the repo MUST create or update the corresponding stable specs under `openspec/specs/` before archive closeout finishes

### Requirement: Completed changes move out of the active change set
The repository MUST archive completed OpenSpec changes under `openspec/changes/archive/` once their accepted stable specs are in place.

#### Scenario: Completed change ready for archive
- **WHEN** a change is complete and its accepted capability requirements have been synced
- **THEN** the change MUST move to a dated path under `openspec/changes/archive/` while preserving its proposal, design, tasks, and delta specs

### Requirement: Repo references distinguish active and historical change state
Repository docs and loop prompts MUST not describe completed changes as active once archive closeout is complete.

#### Scenario: Docs reference completed work
- **WHEN** a repo document or loop prompt references a completed change after archive closeout
- **THEN** it MUST refer to the stable spec or archived change history instead of calling that completed change active
