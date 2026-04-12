## MODIFIED Requirements

### Requirement: Loop can create a new evidence-backed change for missing capabilities
The autonomous loop MUST be able to open exactly one new OpenSpec change when the repo, the broader HaaC stack, or the loop itself is missing a required capability and the evidence meets the discovery policy.

#### Scenario: Missing loop capability discovered
- **WHEN** the loop finds a real missing capability in preflight, validation, review, discovery, or bootstrap behavior
- **THEN** it MUST create one narrow evidence-backed OpenSpec change instead of silently working around the issue

#### Scenario: Missing HaaC capability discovered
- **WHEN** the loop finds a real evidence-backed gap in infrastructure, GitOps, security, storage, networking, automation, DRY, or operator parity
- **THEN** it MUST be allowed to create one narrow OpenSpec change that includes the proposed minimal solution

#### Scenario: Evidence is weak
- **WHEN** the loop does not have a failing command, concrete mismatch, or missing contract
- **THEN** it MUST NOT create a new OpenSpec change
