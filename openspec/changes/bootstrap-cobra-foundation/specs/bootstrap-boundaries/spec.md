## MODIFIED Requirements

### Requirement: Internal orchestration stays modular

The main Taskfile MUST stay focused on operator-facing entrypoints and MUST NOT become the dumping ground for internal post-install orchestration.

#### Scenario: Internal post-install flow is added

- **WHEN** the repository adds a post-install or specialized maintenance flow that operators are not expected to invoke directly
- **THEN** that flow MUST live in a subordinate internal task file or equivalent file-backed orchestration surface
- **AND** the main Taskfile MUST only keep the minimal top-level entrypoint needed to call it when appropriate
