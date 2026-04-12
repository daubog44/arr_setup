# autonomous-loop-runner Specification

## Purpose
Define the stable contract for the repo-local autonomous loop runner, its readiness checks, and browser-backed endpoint verification behavior.
## Requirements
### Requirement: Repo provides an autonomous loop runner
The repository MUST provide a supported autonomous loop runner that uses the official OpenSpec CLI state, creates a session worklog, and launches CodexPotter from a deterministic bootstrap.

#### Scenario: Active change apply mode
- **WHEN** the operator runs the supported loop apply entrypoint
- **THEN** the runner MUST validate local readiness, identify the active OpenSpec changes, create or reuse a session worklog, and launch CodexPotter with a prompt that targets the first active change with pending tasks

#### Scenario: Discovery mode
- **WHEN** the operator runs the supported loop discovery entrypoint
- **THEN** the runner MUST launch CodexPotter with a prompt that performs narrow evidence-based discovery instead of normal apply mode

### Requirement: Repo provides loop readiness checks
The repository MUST expose a loop readiness check that validates the runner prerequisites and current OpenSpec change state before a long-running autonomous session starts.

#### Scenario: Readiness check passes
- **WHEN** the operator runs the readiness entrypoint and all required tools, docs, and active changes are valid
- **THEN** the runner MUST report success without launching CodexPotter

#### Scenario: Readiness check fails
- **WHEN** a required tool, document, or active OpenSpec validation fails
- **THEN** the runner MUST stop before launch and report the missing prerequisite or validation failure

### Requirement: Loop performs browser-level public URL verification
When a loop round reaches public endpoint verification, the loop MUST use Playwright MCP for browser-level navigation checks in addition to HTTP-level verification, unless the MCP is unavailable in the active runtime.

#### Scenario: Playwright MCP available
- **WHEN** the loop reaches a round that emits or verifies public URLs and Playwright MCP is available
- **THEN** it MUST navigate the reported URLs in a browser context and record whether each URL is navigable, redirects to the expected auth flow, or fails

#### Scenario: Playwright MCP unavailable
- **WHEN** the loop reaches public URL verification but Playwright MCP is not exposed in the active runtime
- **THEN** it MUST say that explicitly and fall back to the best available non-browser verification
