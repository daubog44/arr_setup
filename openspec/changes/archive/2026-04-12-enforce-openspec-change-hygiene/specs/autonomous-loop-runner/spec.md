## MODIFIED Requirements

### Requirement: Repo provides an autonomous loop runner
The repository MUST provide a supported autonomous loop runner that uses the official OpenSpec CLI state, surfaces OpenSpec change-surface hygiene debt when completed or scaffold-only changes remain, creates or reuses a session worklog whose header reflects the effective session mode and selected active changes, and launches CodexPotter from a deterministic bootstrap.

#### Scenario: No active change but OpenSpec closeout debt exists
- **WHEN** the operator runs a supported loop entrypoint and no active OpenSpec change matches the current scope, but one or more completed unarchived changes still exist under `openspec/changes/`
- **THEN** the runner MUST surface that completed-change closeout debt in the session context instead of presenting the repo as cleanly idle

#### Scenario: No active change but scaffold-only debt exists
- **WHEN** the operator runs a supported loop entrypoint and the repo contains change directories whose on-disk contents are only `.openspec.yaml`
- **THEN** the runner MUST surface that scaffold debt in the session context so the loop can classify it as OpenSpec hygiene work

### Requirement: Repo provides loop readiness checks
The repository MUST expose a loop readiness check that validates the runner prerequisites and current OpenSpec change state before a long-running autonomous session starts.

#### Scenario: Readiness finds change-surface hygiene debt
- **WHEN** the operator runs the readiness entrypoint and the OpenSpec tree has completed-change closeout debt or scaffold-only change directories
- **THEN** the runner MUST report that debt explicitly even if no active change is currently available
