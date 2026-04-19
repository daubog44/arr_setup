## ADDED Requirements

### Requirement: Jellyfin exposes baseline repo-managed media libraries

The media post-install bootstrap MUST ensure Jellyfin exposes the baseline virtual folders required by the repo-managed ARR stack.

#### Scenario: Missing Jellyfin libraries are created from repo-managed paths

- **WHEN** Jellyfin has no virtual folders for the repo-managed movie and TV paths
- **THEN** media post-install MUST create a Movies library mapped to `/data/movies`
- **AND** it MUST create a TV Shows library mapped to `/data/tv`

#### Scenario: Existing matching libraries are left intact

- **WHEN** Jellyfin already has virtual folders that match the repo-managed names or paths
- **THEN** media post-install MUST NOT create duplicates
