## MODIFIED Requirements

### Requirement: Media post-install verifies the repo-managed ARR stack

The repo-managed ARR bootstrap MUST verify the supported application surfaces before declaring the media stack ready.

#### Scenario: ARR application service probes

- **WHEN** the media post-install bootstrap checks Radarr, Sonarr, and Prowlarr over direct service port-forwards
- **THEN** it MUST require HTTP `200`
- **AND** it MUST accept the deployed healthy `/ping` body that reports `OK`
- **AND** it MUST fail if the returned body does not reflect healthy service state
