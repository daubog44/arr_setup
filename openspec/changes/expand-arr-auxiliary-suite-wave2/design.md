## Scope

This wave is intentionally narrower than "add everything from mediastack".

Priority 1:

- `Lidarr` for music acquisition, using the existing qBittorrent/Gluetun path and the existing Prowlarr topology
- `SABnzbd` as the first supported Usenet client, because it is present in `geekau/mediastack` and has an established exporter ecosystem for Prometheus

Priority 2:

- Seerr/Jellyfin polish only where the new auxiliary services require it
- Homepage/Grafana additions for the new services

Explicitly deferred from this wave:

- `Huntarr`, because the current `geekau/mediastack` README marks it as deprecated
- `Readarr`, `Mylar`, `Whisparr`, `Tdarr`, and other niche/adjacent apps, because they increase storage, metadata, and lifecycle scope beyond the first auxiliary wave

## Design choices

### 1. Keep the acquisition boundary explicit

The current movies/TV stack already has a stable acquisition contract:

- Prowlarr owns indexer fan-out
- qBittorrent/QUI owns torrent acquisition through Gluetun
- Recyclarr owns media quality policy

The auxiliary wave should reuse that boundary instead of introducing a second torrent client or an ad-hoc side path.

### 2. Add SABnzbd as a distinct client, not a replacement

SABnzbd is complementary to qBittorrent, not a replacement:

- qBittorrent remains the torrent path
- SABnzbd becomes the repo-managed Usenet path
- Prowlarr should be able to connect to both the Lidarr service and SABnzbd where applicable

### 3. Only ship apps with an explicit observability story

Each newly supported service must define one of:

- a native `/metrics` endpoint
- a supported Prometheus exporter sidecar/deployment

Grafana should receive at least one curated dashboard or dashboard section per new supported service.

### 4. Preserve the current Seerr/Jellyfin contract

The official Seerr docs reinforce the current design:

- the internal Jellyfin URL is the service URL Seerr should use
- the owner account is the bootstrap/API authority for Seerr

This wave should preserve those assumptions rather than introduce external/public URLs into internal service bootstrap.

## Validation plan

- OpenSpec validation
- focused unit coverage for new bootstrap helpers and manifest contracts
- Helm render
- live `media:post-install`
- live service/API verification for Lidarr and SABnzbd
- Playwright/browser verification for any new public routes
