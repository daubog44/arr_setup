## ADDED Requirements

### Requirement: qBittorrent converges on shared download paths

The repo-managed downloader bootstrap MUST ensure that qBittorrent persists its save and temporary paths on the shared `/data/torrents` surface before other media integrations consume downloader state.

#### Scenario: Invalid legacy save paths are corrected on rerun

- **WHEN** qBittorrent is configured with save or temp paths outside the supported shared `/data` topology
- **THEN** the supported bootstrap MUST update qBittorrent so completed downloads land under `/data/torrents`
- **AND** incomplete downloads land under `/data/torrents/incomplete`

#### Scenario: Reruns preserve the supported path contract

- **WHEN** qBittorrent already persists the supported shared paths
- **THEN** the bootstrap MUST leave the configuration unchanged
- **AND** downstream ARR integrations may rely on those paths without introducing additional path mapping drift
