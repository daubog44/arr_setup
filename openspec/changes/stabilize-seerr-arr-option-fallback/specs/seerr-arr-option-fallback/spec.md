## ADDED Requirements

### Requirement: Seerr ARR option discovery tolerates stale empty root-folder caches

The media post-install bootstrap MUST recover when Seerr test endpoints return empty root-folder lists even though direct ARR state already exposes the supported root folders.

#### Scenario: Direct ARR root folders backfill a stale Seerr test response

- **WHEN** Seerr test output contains an empty `rootFolders` list for Radarr or Sonarr
- **AND** the direct ARR API exposes the supported root folder
- **THEN** the bootstrap MUST use the direct ARR root folder for Seerr settings payload selection

#### Scenario: Non-empty Seerr root folders remain preferred

- **WHEN** Seerr test output already contains the expected root-folder list
- **THEN** the bootstrap MUST continue using the Seerr-provided root-folder data without overriding it
