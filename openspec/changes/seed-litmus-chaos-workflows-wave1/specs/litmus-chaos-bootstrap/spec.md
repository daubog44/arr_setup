## MODIFIED Requirements

### Requirement: Litmus chaos bootstrap is operator-free

The bootstrap path MUST automate Litmus chaos infrastructure enrollment for the canonical environment and MUST remove legacy Litmus environments from the visible operator path.

#### Scenario: Canonical Litmus environment is reconciled

- **WHEN** the Litmus platform is healthy enough for API access
- **THEN** the bootstrap MUST ensure the canonical `haac-default` environment and default chaos infrastructure exist without manual YAML download/apply
- **AND** it MUST seed the repo-managed default workflow template catalog for that project

#### Scenario: Default workflow catalog is seeded

- **WHEN** the default Litmus infrastructure is active
- **THEN** the repo MUST register the expected homelab-safe workflow templates through the Litmus API
- **AND** the operator MUST be able to reach those templates from the Litmus UI without importing YAML manually
