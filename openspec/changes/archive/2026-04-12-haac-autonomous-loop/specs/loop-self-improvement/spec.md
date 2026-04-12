## ADDED Requirements

### Requirement: Loop can create a new evidence-backed change for missing capabilities
The autonomous loop MUST be able to open exactly one new OpenSpec change when the repo or the loop itself is missing a required capability and the evidence meets the discovery policy.

#### Scenario: Missing loop capability discovered
- **WHEN** the loop finds a real missing capability in preflight, validation, review, discovery, or bootstrap behavior
- **THEN** it MUST create one narrow evidence-backed OpenSpec change instead of silently working around the issue

#### Scenario: Evidence is weak
- **WHEN** the loop does not have a failing command, concrete mismatch, or missing contract
- **THEN** it MUST NOT create a new OpenSpec change

## MODIFIED Requirements

### Requirement: One-command bootstrap is a reviewed operator contract
The repository SHALL treat `task up` or its supported wrappers as a reviewed operator contract, and autonomous work affecting that path MUST pass through validation and review gates before being considered complete.

#### Scenario: Bootstrap-affecting change is closed
- **WHEN** a change touches the bootstrap path, the loop runner, or the repo operator contract
- **THEN** the loop MUST require the validation ladder and targeted review coverage described by the repo docs before closeout
