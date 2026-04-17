## MODIFIED Requirements

### Requirement: Litmus chaos bootstrap is operator-free

The bootstrap path MUST automate Litmus chaos infrastructure enrollment for the canonical environment and MUST remove legacy Litmus environments from the visible operator path.

#### Scenario: Canonical Litmus environment is reconciled

- **WHEN** the Litmus platform is healthy enough for API access
- **THEN** the bootstrap MUST ensure the canonical `haac-default` environment and default chaos infrastructure exist without manual YAML download/apply
- **AND** it MUST seed the repo-managed default chaos experiment catalog for that project

#### Scenario: Default chaos catalog is seeded

- **WHEN** the default Litmus infrastructure is active
- **THEN** the repo MUST register the expected homelab-safe chaos experiments through the Litmus API
- **AND** the operator MUST be able to reach those experiments from the Litmus UI without importing YAML manually

#### Scenario: Supporting chaos manifests stay bounded to the catalog contract

- **WHEN** the bootstrap applies supporting manifests for the saved experiment catalog
- **THEN** those manifests MUST resolve from inside the repo-managed Litmus catalog directory
- **AND** they MUST be validated as `ChaosExperiment` objects targeting the `litmus` namespace before apply

#### Scenario: Wave1 catalog removal requires explicit cleanup

- **WHEN** a saved chaos experiment or supporting manifest is removed from the wave1 catalog
- **THEN** the bootstrap MAY leave the previously seeded Litmus experiment or `ChaosExperiment` in place
- **AND** the change documentation MUST describe that manual cleanup is currently required
