## MODIFIED Requirements

### Requirement: The repo-managed arr stack includes a request-management surface

The repo-managed ARR stack MUST prepare Jellyfin for Seerr discovery before Seerr attempts to sync libraries.

#### Scenario: Jellyfin libraries precede Seerr sync

- **WHEN** `media:post-install` configures Seerr against Jellyfin
- **THEN** it MUST ensure the baseline Jellyfin libraries exist first
- **AND** Seerr library sync MUST not fail only because Jellyfin had no virtual folders configured
