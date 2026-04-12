## ADDED Requirements

### Requirement: Loop reuses the current session worklog
The autonomous loop runner MUST reuse the current same-day worklog for repeated `run`, `prompt`, or `worklog` invocations that target the same slug, instead of creating a fresh minute-stamped file for each later helper call.

#### Scenario: Matching same-day worklog already exists
- **WHEN** the operator runs a supported loop helper for a slug that already has one or more same-day worklog files
- **THEN** the runner MUST reuse the most recently updated matching worklog, synchronize its generated header lines, and render prompts against that same path

#### Scenario: No matching worklog exists yet
- **WHEN** the operator runs a supported loop helper for a slug that does not yet have a same-day worklog
- **THEN** the runner MUST create one new minute-stamped worklog file and use that file as the current session worklog
