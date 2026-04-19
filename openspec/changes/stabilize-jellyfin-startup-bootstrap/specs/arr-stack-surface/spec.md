## MODIFIED Requirements

### Requirement: The repo-managed arr stack includes a request-management surface

The repo-managed ARR stack MUST be able to initialize Seerr against the repo-managed Jellyfin service without manual first-run intervention.

#### Scenario: Jellyfin startup bootstrap precedes Seerr auth

- **WHEN** `media:post-install` runs against a first-run Jellyfin instance
- **THEN** it MUST complete the Jellyfin startup bootstrap before calling Seerr Jellyfin auth
- **AND** Seerr MUST see a stable Jellyfin admin auth surface instead of an empty first-run server
