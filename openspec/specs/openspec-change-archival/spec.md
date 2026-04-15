# openspec-change-archival Specification

## Purpose
Define how completed OpenSpec changes are synced into stable specs and archived so the active change set stays meaningful.
## Requirements
### Requirement: Completed changes sync accepted capabilities into stable specs
The repository MUST sync the accepted requirements from a completed OpenSpec change into `openspec/specs/<capability>/spec.md` before the change is treated as closed history.

#### Scenario: Completed change with accepted delta specs
- **WHEN** an OpenSpec change is complete and its accepted requirements exist only inside `openspec/changes/<change>/specs/`
- **THEN** the repo MUST create or update the corresponding stable specs under `openspec/specs/` before archive closeout finishes

### Requirement: Completed changes move out of the active change set

The repository MUST archive bootstrap changes that are no longer the live source of pending work once their accepted requirements are represented in stable specs.

#### Scenario: In-progress change is superseded by accepted stable behavior

- **WHEN** a bootstrap change still appears in `openspec list` but the accepted behavior is already implemented and synced into stable specs
- **THEN** that change MUST be archived instead of remaining in the active backlog
- **AND** the remaining active change set MUST reflect only unresolved observable outcomes

### Requirement: Repo references distinguish active and historical change state
Repository docs and loop prompts MUST not describe completed changes as active once archive closeout is complete.

#### Scenario: Docs reference completed work
- **WHEN** a repo document or loop prompt references a completed change after archive closeout
- **THEN** it MUST refer to the stable spec or archived change history instead of calling that completed change active
