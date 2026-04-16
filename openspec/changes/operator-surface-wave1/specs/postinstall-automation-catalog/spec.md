## ADDED Requirements

### Requirement: Post-install automation definitions live outside the primary operator Taskfile

The system MUST keep post-install automation definitions in dedicated repo-managed files that are consumed by post-install automation, not as ad hoc inline logic in the primary operator Taskfile.

#### Scenario: Post-install automation is rendered

- **WHEN** the repo renders post-install bootstrap resources
- **THEN** the maintenance automation definitions MUST come from dedicated repo-managed files outside the primary operator Taskfile
- **AND** those files MUST be consumable by the post-install bootstrap path without requiring manual operator execution
