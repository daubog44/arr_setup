## Context

The repo already runs qBittorrent/QUI behind Gluetun, with a stable internal service topology:

- qBittorrent HTTP: `qbittorrent.media.svc.cluster.local:8080`
- Prowlarr HTTP: `prowlarr.media.svc.cluster.local:80`
- Radarr HTTP: `radarr.media.svc.cluster.local:80`
- Sonarr HTTP: `sonarr.media.svc.cluster.local:80`

The bootstrap already knows how to read ARR API keys from the live `config.xml` files and how to authenticate to qBittorrent using the downloader credentials derived from `.env`.

The missing capability is not reachability; it is deterministic API wiring between the services.

## Goals / Non-Goals

**Goals:**
- Create or update qBittorrent as the default download client in Radarr, Sonarr, and Prowlarr.
- Create or update Prowlarr application links for Radarr and Sonarr.
- Keep the wiring idempotent so reruns update drift instead of duplicating entries.

**Non-Goals:**
- This wave does not onboard external indexers that require provider credentials.
- This wave does not add TRaSH/Recyclarr quality profiles yet.
- This wave does not add Bazarr, Unpackerr, Lidarr, Readarr, or other suite expansion apps yet.

## Decisions

### 1. Build payloads from the official schema endpoints

Use the live schema endpoints exposed by Radarr, Sonarr, and Prowlarr to derive the payload contracts for:

- `QBittorrent` download clients
- `Radarr` application links
- `Sonarr` application links

Then fill only the repo-managed fields that must differ from defaults, such as internal service URLs, credentials, categories, and enabled state.

Rejected alternative:
- Hardcode full request bodies copied from the current UI implementation. That is brittle across upstream schema changes and less self-describing than starting from the service-provided defaults.

### 2. Keep categories explicit and stable

Use stable categories so downstream behavior is predictable:

- Radarr: `radarr`
- Sonarr: `tv-sonarr`
- Prowlarr default torrent client category: `prowlarr`

These match the default schema expectations and avoid hidden drift.

### 3. Reconcile by name and implementation

Existing items should be matched by implementation plus stable name. If found, update them; if absent, create them. This keeps reruns idempotent and prevents duplicate qBittorrent or app-link entries.

## Risks / Trade-offs

- [Risk] Upstream schema defaults can shift. -> Mitigation: derive payloads from the live schema on each run instead of baking static payload shapes into the repo.
- [Risk] qBittorrent authentication could drift from the bootstrap secret. -> Mitigation: keep using the existing downloader bootstrap and fail the media post-install flow closed if qBittorrent does not accept the reconciled credentials.
