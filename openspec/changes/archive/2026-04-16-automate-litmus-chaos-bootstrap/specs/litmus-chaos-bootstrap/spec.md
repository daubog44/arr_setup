## ADDED Requirements

### Requirement: Litmus chaos bootstrap must be operator-free

The bootstrap path MUST automate the Litmus chaos infrastructure enrollment.

#### Scenario: no default environment exists

- **WHEN** the Litmus control plane is installed and reachable
- **THEN** the bootstrap MUST create a default environment automatically
- **AND** the operator MUST NOT be required to create the environment in the UI

#### Scenario: no chaos infrastructure is active for the default environment

- **WHEN** the default environment exists but has no active confirmed chaos infrastructure
- **THEN** the bootstrap MUST register a default infrastructure through the Litmus control-plane APIs
- **AND** it MUST apply the returned manifest to the cluster automatically
- **AND** it MUST wait until the infrastructure is active and confirmed

#### Scenario: stale inactive default infrastructure exists

- **WHEN** a stale default infrastructure record exists but is not active
- **THEN** the bootstrap MUST repair the state automatically without requiring the operator to download or apply Litmus-generated YAML manually

#### Scenario: bootstrap verification

- **WHEN** `task up` or `task reconcile:gitops` completes
- **THEN** Litmus MUST expose a usable default environment with a confirmed chaos infrastructure
- **AND** the verification path MUST fail if the UI still depends on the manual “download/apply YAML” flow
