## MODIFIED Requirements

### Requirement: Published routes reflect the real supported media catalog

The repo-managed public media catalog MUST describe which published routes are request brokers and which are standalone ARR surfaces.

#### Scenario: Whisparr is exposed to the operator

- **WHEN** the repo publishes a Whisparr route
- **THEN** the operator-facing docs and Homepage surface MUST identify it as a standalone ARR-like workload
- **AND** they MUST NOT imply that Seerr can broker Whisparr requests

