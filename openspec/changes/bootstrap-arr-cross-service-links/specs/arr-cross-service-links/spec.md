## ADDED Requirements

### Requirement: Core ARR services are wired together during media post-install

The media post-install bootstrap MUST reconcile the repo-managed qBittorrent, Prowlarr, Radarr, and Sonarr integrations so the ARR stack can process requests without manual UI setup.

#### Scenario: Missing qBittorrent clients are created

- **WHEN** Radarr, Sonarr, or Prowlarr exposes no qBittorrent download client matching the repo-managed internal service topology
- **THEN** the bootstrap MUST create one through the official API using the repo-managed downloader credentials

#### Scenario: Existing qBittorrent clients are updated on rerun

- **WHEN** a qBittorrent client already exists but drifts from the repo-managed internal URL, credentials, or categories
- **THEN** the bootstrap MUST update that client instead of creating a duplicate

### Requirement: Prowlarr application links are bootstrapped

Prowlarr MUST expose repo-managed application links for Radarr and Sonarr after `media:post-install`.

#### Scenario: Missing downstream app links are created

- **WHEN** Prowlarr has no Radarr or Sonarr application matching the repo-managed cluster services
- **THEN** the bootstrap MUST create the missing application links using the live ARR API keys

#### Scenario: Existing downstream app links are updated on rerun

- **WHEN** a Prowlarr Radarr or Sonarr application exists but drifts from the repo-managed URL or API key
- **THEN** the bootstrap MUST update that application instead of creating a duplicate
