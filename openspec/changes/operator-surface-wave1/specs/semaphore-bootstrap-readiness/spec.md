## ADDED Requirements

### Requirement: Semaphore maintenance schedules are catalog-driven, named, and active

The Semaphore bootstrap path MUST reconcile maintenance schedules from a repo-managed post-install catalog, and the resulting schedules MUST be persisted as named active schedules.

#### Scenario: Bootstrap reconciles maintenance schedules

- **WHEN** the Semaphore bootstrap job reconciles the managed maintenance project
- **THEN** each repo-managed schedule MUST be created or updated with a stable non-empty display name
- **AND** each managed schedule MUST persist as active in the Semaphore API

#### Scenario: Catalog change updates existing schedules in place

- **WHEN** the repo-managed post-install catalog changes an existing schedule definition
- **THEN** a later bootstrap run MUST update the existing managed schedule in place
- **AND** it MUST NOT create duplicate schedules for the same managed template
