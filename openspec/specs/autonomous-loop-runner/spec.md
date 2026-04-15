# autonomous-loop-runner Specification

## Purpose
Define the stable contract for the repo-local autonomous loop runner, its readiness checks, and browser-backed endpoint verification behavior.
## Requirements
### Requirement: Repo provides an autonomous loop runner

The repository MUST provide a supported autonomous loop runner that uses the official OpenSpec CLI state, surfaces OpenSpec change-surface hygiene debt when completed or scaffold-only changes remain, creates or reuses a session worklog whose header reflects the effective session mode and selected active changes, and launches CodexPotter from a deterministic bootstrap.

#### Scenario: Active change finishes during a round

- **WHEN** the loop finishes the active change and no further actionable tasks remain in the requested scope
- **THEN** the loop SHOULD stop cleanly instead of spinning on no-op work
- **AND** if it discovers one new evidence-backed gap that is still in scope, it MAY open exactly one new change before stopping or continuing according to the round budget

### Requirement: Repo provides loop readiness checks
The repository MUST expose a loop readiness check that validates the runner prerequisites and current OpenSpec change state before a long-running autonomous session starts.

#### Scenario: Readiness finds change-surface hygiene debt
- **WHEN** the operator runs the readiness entrypoint and the OpenSpec tree has completed-change closeout debt or scaffold-only change directories
- **THEN** the runner MUST report that debt explicitly even if no active change is currently available

### Requirement: Loop performs browser-level public URL verification
When a loop round reaches public endpoint verification, the loop MUST use Playwright MCP for browser-level navigation checks in addition to HTTP-level verification, unless the MCP is unavailable in the active runtime.

#### Scenario: Playwright MCP available
- **WHEN** the loop reaches a round that emits or verifies public URLs and Playwright MCP is available
- **THEN** it MUST navigate the reported URLs in a browser context and record whether each URL is navigable, redirects to the expected auth flow, or fails

#### Scenario: Playwright MCP unavailable
- **WHEN** the loop reaches public URL verification but Playwright MCP is not exposed in the active runtime
- **THEN** it MUST say that explicitly and fall back to the best available non-browser verification

### Requirement: Loop reuses the current session worklog
The autonomous loop runner MUST reuse the current same-day worklog for repeated `run`, `prompt`, or `worklog` invocations that target the same slug, instead of creating a fresh minute-stamped file for each later helper call.

#### Scenario: Matching same-day worklog already exists
- **WHEN** the operator runs a supported loop helper for a slug that already has one or more same-day worklog files
- **THEN** the runner MUST reuse the most recently updated matching worklog, synchronize its generated header lines, and render prompts against that same path

#### Scenario: No matching worklog exists yet
- **WHEN** the operator runs a supported loop helper for a slug that does not yet have a same-day worklog
- **THEN** the runner MUST create one new minute-stamped worklog file and use that file as the current session worklog

