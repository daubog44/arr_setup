## MODIFIED Requirements

### Requirement: Repo provides an autonomous loop runner
The repository MUST provide a supported autonomous loop runner that uses the official OpenSpec CLI state, creates or reuses a session worklog whose header reflects the effective session mode and selected active changes, and launches CodexPotter from a deterministic bootstrap.

#### Scenario: Active change apply mode
- **WHEN** the operator runs the supported loop apply entrypoint and one or more active OpenSpec changes match the session scope
- **THEN** the runner MUST validate local readiness, identify the active OpenSpec changes, create or reuse a session worklog, and launch CodexPotter with an apply-mode prompt that targets the first active change with pending tasks

#### Scenario: Apply request falls back to discovery
- **WHEN** the operator requests apply mode but no active OpenSpec change matches the current session scope
- **THEN** the runner MUST resolve the session to discovery mode before creating or updating the session worklog header and before rendering the prompt used for that session

#### Scenario: Discovery mode
- **WHEN** the operator runs the supported loop discovery entrypoint
- **THEN** the runner MUST create or reuse a session worklog and launch CodexPotter with a prompt that performs narrow evidence-based discovery instead of normal apply mode

#### Scenario: Standalone session artifact helpers
- **WHEN** the operator uses the standalone loop `prompt` or `worklog` helpers
- **THEN** those helpers MUST use the same effective-mode resolution and selected active-change set as the main `run` command
