## ADDED Requirements

### Requirement: Seerr Jellyfin auth is rerunnable

The media post-install bootstrap MUST select the Seerr Jellyfin auth payload based on whether Seerr already has a Jellyfin media server configured.

#### Scenario: First-run Seerr auth includes server details

- **WHEN** Seerr does not yet report a configured Jellyfin media server
- **THEN** the auth payload MUST include hostname, port, SSL flag, and Jellyfin server type

#### Scenario: Rerun Seerr auth omits already-configured server details

- **WHEN** Seerr already reports Jellyfin as the configured media server
- **THEN** the auth payload MUST omit the server connection fields
- **AND** reruns MUST NOT fail only because Seerr says the Jellyfin hostname is already configured
