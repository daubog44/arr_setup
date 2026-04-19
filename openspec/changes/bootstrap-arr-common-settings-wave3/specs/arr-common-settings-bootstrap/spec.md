## ADDED Requirements

### Requirement: Supported ARR apps reconcile the repo-managed common settings baseline
The media post-install bootstrap MUST reconcile the supported common settings baseline for Radarr, Sonarr, and Lidarr through their public APIs.

#### Scenario: Radarr, Sonarr, and Lidarr expose stock defaults
- **WHEN** `media:post-install` reaches the service-probe phase
- **AND** a supported ARR app still exposes stock defaults such as renaming disabled, empty-folder cleanup disabled, or Linux permissions disabled
- **THEN** the bootstrap MUST persist the repo-managed common settings baseline for that app
- **AND** reruns MUST keep the settings idempotent instead of duplicating or drifting them

### Requirement: Jellyfin exposes the supported music library
The media post-install bootstrap MUST keep Jellyfin's default library set aligned with the supported media managers.

#### Scenario: Lidarr is part of the supported stack
- **WHEN** `media:post-install` reconciles Jellyfin
- **THEN** Jellyfin MUST expose the repo-managed Movies and TV libraries
- **AND** it MUST also expose a Music library for the Lidarr-managed media path

### Requirement: Deferred adjacent apps are documented explicitly
The operator-facing documentation MUST explain which media apps are supported today and why adjacent candidates are deferred.

#### Scenario: Operator reviews the supported media suite
- **WHEN** the operator reads the README media automation contract
- **THEN** the docs MUST list the supported auto-bootstrapped services
- **AND** they MUST explain why adjacent candidates such as deprecated Readarr packaging are not promoted into the default repo-managed stack yet
