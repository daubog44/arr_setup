## ADDED Requirements

### Requirement: ARR media localization and naming are repo-managed

The repo MUST reconcile exact naming templates and language preference settings for the supported ARR media services instead of relying on manual UI edits.

#### Scenario: Media post-install reconciles naming templates

- **WHEN** `media:post-install` configures Radarr, Sonarr, and Lidarr
- **THEN** it MUST persist the repo-managed folder and file naming templates for each supported service
- **AND** reruns MUST detect and repair naming drift

#### Scenario: Italian-first policy is enforced downstream from Seerr

- **WHEN** the operator wants Italian-preferred content for movies and TV
- **THEN** the repo MUST enforce that policy in Radarr and Sonarr using supported quality-profile or custom-format mechanics
- **AND** Seerr MUST continue acting only as the request broker to those services, not as the indexer or language policy engine

