## ADDED Requirements

### Requirement: Recyclarr quality policy is repo-managed

The repo-managed media stack MUST bootstrap a deterministic Recyclarr configuration for the supported Radarr and Sonarr defaults instead of leaving the shipped CronJob on its placeholder config.

#### Scenario: Fresh bootstrap writes the managed Recyclarr config

- **WHEN** `media:post-install` reaches the quality-policy phase on a fresh cluster
- **THEN** it MUST write the repo-managed Recyclarr config and secrets into the existing Recyclarr PVC
- **AND** the generated secrets MUST use the live ARR API keys and internal cluster URLs

#### Scenario: Rerun updates the quality policy in place

- **WHEN** the managed Recyclarr config changes or the downstream ARR API keys drift
- **THEN** `media:post-install` MUST update the Recyclarr config and rerun sync instead of requiring manual PVC edits

### Requirement: Supported Sonarr and Radarr defaults converge through Recyclarr

The repo-managed default Radarr and Sonarr quality policy MUST be applied by Recyclarr during bootstrap.

#### Scenario: Quality sync completes during media post-install

- **WHEN** `media:post-install` runs after the ARR services are reachable
- **THEN** Recyclarr sync MUST run successfully for the supported Sonarr and Radarr instances
