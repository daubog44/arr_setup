## ADDED Requirements

### Requirement: Media post-install manages the qBittorrent ARR category contract

The supported media post-install phase MUST reconcile the qBittorrent categories used by the repo-managed ARR clients.

#### Scenario: qBittorrent categories are reconciled

- **WHEN** the operator runs `media:post-install`
- **THEN** qBittorrent MUST expose managed categories for the repo-managed ARR clients
- **AND** each managed category MUST persist the repo-managed save path under `/data/torrents`

#### Scenario: qBittorrent category persistence fails

- **WHEN** the operator cannot create or correct a managed qBittorrent category through the supported WebUI API
- **THEN** `media:post-install` MUST fail closed
- **AND** the operator output MUST name the qBittorrent category contract as the blocker
