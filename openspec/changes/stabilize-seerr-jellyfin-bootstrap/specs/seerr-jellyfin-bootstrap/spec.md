## ADDED Requirements

### Requirement: Seerr Jellyfin bootstrap uses the real auth payload

The media post-install bootstrap MUST send the Jellyfin connection fields required by Seerr when authenticating through `/api/v1/auth/jellyfin`.

#### Scenario: First-time Seerr setup authenticates against in-cluster Jellyfin

- **WHEN** Seerr is not yet initialized and media post-install signs in through the Jellyfin auth route
- **THEN** the request payload MUST include the Jellyfin username and password
- **AND** it MUST include the internal Jellyfin hostname, port, SSL flag, and Jellyfin server type
- **AND** the bootstrap MUST NOT fail only because Seerr reports `No hostname provided.`
