## MODIFIED Requirements

### Requirement: Public media UI behavior is documented from the real upstream integration contract

The repo documentation for the media request surface MUST describe which downstream services Seerr can actually control.

#### Scenario: The operator asks how Seerr sees available content

- **WHEN** the operator reads the repo-managed media documentation
- **THEN** it MUST explain that Seerr integrates with Jellyfin, Radarr, and Sonarr
- **AND** it MUST explain that indexer selection happens through Prowlarr and the downstream ARR services rather than inside Seerr itself

