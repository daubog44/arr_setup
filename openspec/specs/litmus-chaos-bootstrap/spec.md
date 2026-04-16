# litmus-chaos-bootstrap Specification

## Purpose
Make the Litmus post-install path operator-free by automatically enrolling a working default chaos infrastructure during bootstrap and reconcile flows.
## Requirements
### Requirement: Litmus chaos bootstrap is operator-free

The bootstrap path MUST automate Litmus chaos infrastructure enrollment for the canonical environment and MUST remove legacy Litmus environments from the visible operator path.

#### Scenario: Legacy `test` environment still exists

- **WHEN** Litmus still contains the legacy `test` environment
- **THEN** the bootstrap MUST migrate that legacy environment out of the visible UI path once the canonical `haac-default` environment is healthy
- **AND** the operator MUST NOT be sent through the manual "download/apply YAML" flow through the legacy environment

