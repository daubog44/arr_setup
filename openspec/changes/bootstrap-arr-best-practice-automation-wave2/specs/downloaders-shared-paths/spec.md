## MODIFIED Requirements

### Requirement: qBittorrent shared storage paths are explicit and supported

The supported qBittorrent shared-path contract MUST include the managed ARR category save paths, not only the default save and temp paths.

#### Scenario: Downloader shared-path contract is rendered

- **WHEN** the repo-managed downloader manifest is rendered
- **THEN** it MUST declare the shared default save and temp paths under `/data/torrents`
- **AND** it MUST create the managed ARR category directories under that same shared root

#### Scenario: Downloader shared-path contract is verified live

- **WHEN** the operator verifies the qBittorrent surface after `media:post-install`
- **THEN** it MUST confirm the default save and temp paths
- **AND** it MUST confirm the managed ARR categories with their expected save paths
