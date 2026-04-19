## ADDED Requirements

### Requirement: ARR root folders are bootstrapped before Seerr discovery

The media post-install bootstrap MUST ensure that Radarr and Sonarr expose the repo-managed root folders required by Seerr before Seerr requests ARR integration options.

#### Scenario: Missing root folders are created on first run

- **WHEN** Radarr or Sonarr exposes no root folder matching the repo-managed media topology
- **THEN** the bootstrap MUST create the supported root folder through the official ARR root-folder API

#### Scenario: Existing root folders are preserved on rerun

- **WHEN** the supported root folder is already present in Radarr or Sonarr
- **THEN** the bootstrap MUST NOT create a duplicate
- **AND** reruns MUST continue to Seerr ARR configuration instead of failing on an empty option list
