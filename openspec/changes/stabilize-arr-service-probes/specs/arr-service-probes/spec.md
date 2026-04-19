## ADDED Requirements

### Requirement: ARR service probes accept the deployed healthy `/ping` response

The media post-install bootstrap MUST treat the current healthy `/ping` response of the repo-managed ARR applications as a valid success contract.

#### Scenario: Healthy ARR apps return `status: OK`

- **WHEN** Radarr, Sonarr, or Prowlarr responds to `/ping` with HTTP `200`
- **AND** the response body communicates healthy status as `OK`
- **THEN** the ARR service probe MUST pass
- **AND** it MUST NOT fail only because the body is no longer the legacy literal `pong`

#### Scenario: HTML or unrelated success bodies still fail

- **WHEN** the `/ping` request returns HTTP `200`
- **BUT** the body does not communicate the expected healthy status for the ARR app
- **THEN** the service probe MUST still fail with an explicit body-pattern mismatch
