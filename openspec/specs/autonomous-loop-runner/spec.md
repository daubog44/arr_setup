# autonomous-loop-runner Specification

## Purpose
Define the stable contract for the repo-local autonomous loop runner, its readiness checks, and browser-backed endpoint verification behavior.
## Requirements
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

### Requirement: Loop reuses the current session worklog
The autonomous loop runner MUST reuse the current same-day worklog for repeated `run`, `prompt`, or `worklog` invocations that target the same slug, instead of creating a fresh minute-stamped file for each later helper call.

#### Scenario: Matching same-day worklog already exists
- **WHEN** the operator runs a supported loop helper for a slug that already has one or more same-day worklog files
- **THEN** the runner MUST reuse the most recently updated matching worklog, synchronize its generated header lines, and render prompts against that same path

#### Scenario: No matching worklog exists yet
- **WHEN** the operator runs a supported loop helper for a slug that does not yet have a same-day worklog
- **THEN** the runner MUST create one new minute-stamped worklog file and use that file as the current session worklog

