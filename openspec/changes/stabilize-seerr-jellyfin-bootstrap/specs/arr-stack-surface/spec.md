## MODIFIED Requirements

### Requirement: The repo-managed arr stack includes a request-management surface

The repo-managed ARR stack MUST provide a supported path to initialize Seerr against the repo-managed media services.

#### Scenario: Seerr media-server bootstrap

- **WHEN** `media:post-install` initializes Seerr against Jellyfin
- **THEN** it MUST use the real Seerr Jellyfin auth payload contract
- **AND** it MUST authenticate against the in-cluster Jellyfin service before persisting external-facing settings
